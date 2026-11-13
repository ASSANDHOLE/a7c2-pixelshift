"""Minimal Sony Senser authentication + backup snapshots; no USB imports.

Derived from the pinned camera_runtime Senser protocol. See provenance and MIT
notice in docs/READONLY_READER_NOTICES.txt. A USB OUT transfer sends a *request*;
the only permitted research request is BACKUP_PDT_READ (0x603, 5).
"""
import hashlib
import struct
from a7c2_readonly_backup import MAX_SNAPSHOT

NORMAL_PID, SERVICE_PID = 0x0e8a, 0x0336
START, STOP = (0x43, 1, 0x37ff, 0xd7aa), (0x43, 1, 0xc800, 0x2855)
HEADER = struct.Struct('<IHHBBBB')
AUTH = struct.Struct('>HH512s')
SEGMENT, CHUNK = 0x100000, 0x8000


class ProtocolError(RuntimeError):
    pass


class PolicyError(ProtocolError):
    pass


def sony_sha1(data):
    """SHA-1 with Sony's truncated message-length field, per pinned crypto.py."""
    length = len(data) & 31
    message = data + b'\x80'
    message += b'\0' * ((56-len(message) % 64) % 64) + struct.pack('>Q', length*8)
    h = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0]
    def rol(value, count):
        return ((value << count) | (value >> (32-count))) & 0xffffffff
    for offset in range(0, len(message), 64):
        words = list(struct.unpack_from('>16I', message, offset))
        for i in range(16, 80):
            words.append(rol(words[i-3] ^ words[i-8] ^ words[i-14] ^ words[i-16], 1))
        a, b, c, d, e = h
        for i in range(80):
            if i < 20:
                f, k = d ^ (b & (c ^ d)), 0x5a827999
            elif i < 40:
                f, k = b ^ c ^ d, 0x6ed9eba1
            elif i < 60:
                f, k = (b & c) | (b & d) | (c & d), 0x8f1bbcdc
            else:
                f, k = b ^ c ^ d, 0xca62c1d6
            a, b, c, d, e = (rol(a, 5)+f+e+k+words[i]) & 0xffffffff, a, rol(b, 30), c, d
        h = [(x+y) & 0xffffffff for x, y in zip(h, (a, b, c, d, e))]
    return struct.pack('>5I', *h)


class OutgoingPolicy:
    """Enforce the complete small outbound vocabulary at the transport boundary."""
    def __init__(self, pid):
        if pid not in (NORMAL_PID, SERVICE_PID):
            raise PolicyError('Unsupported USB identity')
        self.pid, self.state, self.auth_index, self.sequence = pid, 'new', 0, 1

    def control(self, request):
        if request == START and self.state == 'new':
            self.state = 'auth'
        elif request == STOP and self.pid == SERVICE_PID and self.state == 'ready':
            self.state = 'closed'
        else:
            raise PolicyError('Control transfer outside read-only policy')

    def bulk(self, data):
        if self.state == 'auth':
            if len(data) != AUTH.size or self.auth_index >= 7:
                raise PolicyError('Unexpected authentication packet')
            word, salt, payload = AUTH.unpack(data)
            command = (~word) & 0xffff
            expected = (1, 3, 1, 3, 1, 3, 5)[self.auth_index]
            if salt or command != expected:
                raise PolicyError('Authentication order mismatch')
            if command in (1, 5) and any(payload):
                raise PolicyError('Unexpected authentication payload')
            if command == 3 and (payload[0] != 1 or any(payload[33:])):
                raise PolicyError('Unexpected authentication response size')
            self.auth_index += 1
            return
        if self.state != 'ready' or self.pid != SERVICE_PID or self.sequence > 4:
            raise PolicyError('Snapshot read outside authenticated service session or quota')
        allowed = [HEADER.pack(5, 0x40, self.sequence, 0, 0, 0, 0) +
                   struct.pack('<HHB', 0x603, 5, view) for view in (0, 1)]
        if data not in allowed:
            raise PolicyError('Only fixed backup snapshot reads are permitted')
        self.sequence += 1

    def authenticated(self):
        if self.state != 'auth' or self.auth_index != 7:
            raise PolicyError('Incomplete authentication')
        self.state = 'ready'

    def poison(self):
        self.state = 'failed'


class Protocol:
    def __init__(self, raw, pid, keys, event=lambda *a, **k: None):
        self.raw, self.pid, self.keys, self.event = raw, pid, keys, event
        self.policy = OutgoingPolicy(pid)
        self.healthy = True

    def _write(self, packet):
        self.policy.bulk(packet)
        try:
            self.raw.write(packet)
        except BaseException:
            self.healthy = False
            self.policy.poison()
            raise

    def _read(self, length):
        out, empty = bytearray(), 0
        while len(out) < length:
            data = self.raw.read(length-len(out))
            if len(data) > length-len(out):
                raise ProtocolError('USB read exceeded requested length')
            if not data:
                empty += 1
                if empty > 32:
                    raise ProtocolError('Excessive empty USB transfers')
            else:
                out.extend(data)
        return bytes(out)

    def _auth_exchange(self, command, data=b''):
        self._write(AUTH.pack((~command) & 0xffff, 0, data))
        word, salt, payload = AUTH.unpack(self._read(AUTH.size))
        return ((~word) & 0xffff)-salt, payload

    def authenticate(self):
        self.raw.begin(30)
        self.policy.control(START)
        try:
            # The archived transport tolerates a USB error on this control
            # request. A completed authentication is the evidence of success.
            try:
                self.raw.control(START)
            except OSError:
                self.event('start_control_unacknowledged', pid=f'{self.pid:04x}')
            for i in range(3):
                result, data = self._auth_exchange(1)
                if result not in (2, 8):
                    raise ProtocolError('Unexpected authentication challenge')
                family = 'sha1' if result == 2 else 'sha256'
                message = data + self.keys[family][i] if self.pid == SERVICE_PID else data[:4]
                digest = sony_sha1(message) if result == 2 else hashlib.sha256(message).digest()
                result, _ = self._auth_exchange(3, b'\x01'+digest)
                if result != 4:
                    raise ProtocolError('Authentication response rejected')
            result, data = self._auth_exchange(5)
            if result != 6 or data[0] != 1:
                raise ProtocolError('Authentication did not complete')
            self.policy.authenticated()
        except BaseException:
            self.healthy = False
            self.policy.poison()
            raise

    def snapshot(self, from_memory):
        if type(from_memory) is not bool:
            raise PolicyError('Snapshot selector must be a boolean')
        sequence = self.policy.sequence
        packet = HEADER.pack(5, 0x40, sequence, 0, 0, 0, 0) + struct.pack('<HHB', 0x603, 5, int(from_memory))
        self.raw.begin(180)
        try:
            self._write(packet)
            chunks, remaining, total = [], None, 0
            while True:
                size, func, seq, _, _, _, response = HEADER.unpack(self._read(HEADER.size))
                if func != 0x40 or seq != sequence or response != 0:
                    raise ProtocolError('Snapshot response function, sequence or status mismatch')
                if not 0 < size <= MAX_SNAPSHOT or (remaining is not None and size != remaining):
                    raise ProtocolError('Snapshot continuation length mismatch or exceeds limit')
                take = min(size, SEGMENT)
                if total + take > MAX_SNAPSHOT:
                    raise ProtocolError('Snapshot exceeds total size ceiling')
                for offset in range(0, take, CHUNK):
                    chunks.append(self._read(min(CHUNK, take-offset)))
                total += take
                if size <= SEGMENT:
                    break
                remaining = size-SEGMENT
            return b''.join(chunks)
        except BaseException:
            self.healthy = False
            self.policy.poison()
            raise

    def stop(self):
        self.raw.begin(10)
        self.policy.control(STOP)
        self.raw.control(STOP)
