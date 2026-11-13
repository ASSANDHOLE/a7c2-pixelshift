"""Bounded, read-only BK4 parser. No device, network or upstream executable imports.

Format derived from the pinned pmca/backup/__init__.py; provenance and notices
are in sources/readonly-reader.json and docs/READONLY_READER_NOTICES.txt.
"""
from dataclasses import dataclass
import hashlib
import struct

MAX_SNAPSHOT = 16 * 1024 * 1024
TARGETS = ((1, 0x0f0025), (1, 0x0f0001), (1, 0x0f0028),
           (1, 0x0f0029), (1, 0x0f002c), (1, 0x02d00000))


class BackupError(ValueError):
    pass


@dataclass(frozen=True)
class Property:
    attr: int
    data: bytes
    reset: bytes | None


@dataclass
class Block:
    offset: int
    size: int
    properties: dict


def parse_block(raw, start):
    if start < 0 or start + 256 > len(raw) or raw[start+12:start+16] != b'BK4\0':
        raise BackupError('Invalid BK4 header')
    nsub, nprop, dataoff, datasize, checksum = struct.unpack_from('<IIIII', raw, start+16)
    size = dataoff + datasize
    tableoff = 256 + nsub * 6
    if not (0 < nsub <= 65536 and 0 < nprop <= 300000 and
            tableoff + nprop * 6 <= dataoff <= size <= MAX_SNAPSHOT and start+size <= len(raw)):
        raise BackupError('BK4 lengths or tables outside bounds')
    block = memoryview(raw)[start:start+size]
    if sum(block[:32]) + sum(block[36:]) != checksum:
        raise BackupError('BK4 checksum mismatch')
    props = {}
    for sid in range(nsub):
        count, first = struct.unpack_from('<HI', block, 256+sid*6)
        if first + count > nprop:
            raise BackupError('Subsystem exceeds property table')
        for index in range(count):
            attr, ptr = struct.unpack_from('<HI', block, tableoff+(first+index)*6)
            if ptr == 0xffffffff:
                continue
            length, off = ptr >> 24, ptr & 0xffffff
            maximum = length
            if not dataoff <= off <= size:
                raise BackupError('Property offset outside data section')
            if length == 255:
                if off + 2 > size:
                    raise BackupError('Truncated oversized length')
                length = maximum = struct.unpack_from('<H', block, off)[0]
                off += 2
            elif length == 0:
                if off + 4 > size:
                    raise BackupError('Truncated variable length')
                length, maximum = struct.unpack_from('<HH', block, off)
                off += 4
            if length > maximum or off + maximum > size:
                raise BackupError('Property extent outside block')
            reset = None
            if attr & 0x74:
                if off + maximum + length > size:
                    raise BackupError('Reset-data extent outside block')
                reset = bytes(block[off+maximum:off+maximum+length])
            props[sid << 16 | index] = Property(attr, bytes(block[off:off+length]), reset)
    return Block(start, size, props)


def parse_snapshot(raw):
    if not 512 <= len(raw) <= MAX_SNAPSHOT:
        raise BackupError('Snapshot length outside bounds')
    blocks, position, candidates = [], 0, 0
    while True:
        marker = raw.find(b'BK4\0', position)
        if marker < 0:
            break
        position = marker+4
        candidates += 1
        if candidates > 128:
            raise BackupError('Excessive BK4 candidates')
        try:
            block = parse_block(raw, marker-12)
        except (BackupError, struct.error):
            continue
        if blocks and block.offset < blocks[-1].offset + blocks[-1].size:
            raise BackupError('Overlapping valid BK4 blocks')
        blocks.append(block)
    if len(blocks) != 2:
        raise BackupError(f'Expected exactly two valid BK4 blocks; found {len(blocks)}')
    return blocks


def identity_digest(blocks):
    prop = blocks[0].properties.get(0x00e70003)
    if prop is None or len(prop.data) != 4:
        raise BackupError('Missing four-byte body identity in block 0')
    return hashlib.sha256(prop.data).hexdigest()


def selected_records(blocks):
    result = {}
    for block, key in TARGETS:
        prop = blocks[block].properties.get(key)
        result[f'{block}:{key:08x}'] = None if prop is None else dict(
            attr=prop.attr, size=len(prop.data), hex=prop.data.hex(),
            sha256=hashlib.sha256(prop.data).hexdigest())
    return result


def compare_snapshots(snapshots):
    """Input names are memory-1, stored-1, memory-2, stored-2. Output is private."""
    expected = {'memory-1', 'stored-1', 'memory-2', 'stored-2'}
    if set(snapshots) != expected:
        raise BackupError('Four named snapshots required')
    parsed = {name: parse_snapshot(raw) for name, raw in snapshots.items()}
    identities = {identity_digest(blocks) for blocks in parsed.values()}
    if len(identities) != 1:
        raise BackupError('Body identity differs between snapshots')
    records = {name: selected_records(blocks) for name, blocks in parsed.items()}
    missing = {name: [k for k, value in rows.items() if value is None]
               for name, rows in records.items()}
    coefficients = {}
    for name, blocks in parsed.items():
        prop = blocks[1].properties.get(0x0f0025)
        coefficients[name] = list(prop.data[0x70:0x73]) if prop and len(prop.data) == 256 else None
    stable = {view: records[view+'-1'] == records[view+'-2'] for view in ('memory', 'stored')}
    coefficient_stable = {view: coefficients[view+'-1'] is not None and
                         coefficients[view+'-1'] == coefficients[view+'-2'] for view in ('memory', 'stored')}
    return dict(body_sha256=next(iter(identities)), selected_records=records,
                missing_records=missing, coefficients=coefficients, repeat_stable=stable,
                coefficient_repeat_stable=coefficient_stable,
                stored_equals_memory=records['stored-1'] == records['memory-1'],
                research_ready=all(stable.values()) and not any(missing.values()) and
                               all(v is not None for v in coefficients.values()),
                interpretation='Backup views only; no arbitrary CP RAM, motion or recovery validation.')
