"""A7C II 2.01 backup reader. Default/offline commands never import USB modules.

Live commands require --allow-camera-read --firmware 2.01. They perform
authentication and backup reads, not firmware/calibration writes. No recovery,
driver installer, payload upload, generic memory access or arbitrary opcode API.
"""
import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import uuid

from a7c2_readonly_backup import (MAX_SNAPSHOT, BackupError, parse_snapshot,
                                  identity_digest, compare_snapshots)
from a7c2_readonly_protocol import Protocol, NORMAL_PID, SERVICE_PID, START, STOP, PolicyError

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/locks'
SOURCE = ROOT / 'vendor/a7c2'
DEPS = {'pyusb': '1.3.1', 'libusb-package': '1.0.30.0', 'importlib_resources': '6.5.2'}
VIEWS = (('memory-1', True), ('stored-1', False), ('memory-2', True), ('stored-2', False))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    manifest = json.loads((ROOT/'sources/readonly-reader.json').read_text(encoding='utf-8'))
    for row in manifest['inputs']:
        path = (ROOT/row['path']).resolve()
        if not path.is_relative_to(ROOT) or sha(path.read_bytes()) != row['sha256']:
            raise ValueError('Pinned reader source differs: '+row['path'])
    return manifest


def load_keys():
    verify_sources()
    # Parse literal data; do not import the upstream runtime, USB tools or app.
    path = SOURCE/'src/camera_runtime/vendor/pmca/usb/constants.py'
    values = {}
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('senserKeysSha1', 'senserKeysSha256'):
                value = ast.literal_eval(node.value)
                if not isinstance(value, list) or len(value) != 3 or any(type(v) is not bytes or len(v) != 512 for v in value):
                    raise ValueError('Unexpected authentication constant layout')
                values['sha1' if node.targets[0].id.endswith('Sha1') else 'sha256'] = value
    if set(values) != {'sha1', 'sha256'}:
        raise ValueError('Authentication constants missing')
    return values


def preflight():
    """Metadata and file reads only; deliberately no USB import/backend creation."""
    if sys.platform != 'win32' or struct.calcsize('P') != 8 or sys.version_info[:2] != (3, 12):
        raise ValueError('This prepared reader is scoped to Windows x64 / Python 3.12')
    verify_sources()
    load_keys()
    for package, version in DEPS.items():
        if importlib.metadata.version(package) != version:
            raise ValueError('Dependency version mismatch: '+package)
    distribution = importlib.metadata.distribution('libusb-package')
    dlls = [distribution.locate_file(p) for p in distribution.files if str(p).endswith('.dll')]
    if not dlls or not all(p.is_file() for p in dlls):
        raise ValueError('Bundled libusb DLL missing')
    review = json.loads((ROOT/'integrity/transport-review.json').read_text(encoding='utf-8'))
    if review.get('status') != 'offline-passed' or review.get('hardware_validated') is not False:
        raise ValueError('Offline review not complete')
    for path, expected in review['reviewed_files'].items():
        if sha((ROOT/path).read_bytes()) != expected:
            raise ValueError('File changed since offline review: '+path)
    return dict(status='OFFLINE_READY', usb_imported=False, device_access=False,
                firmware='2.01 (user-confirmed, not read by preflight)', dependencies=DEPS)


def private_root():
    resolved = PRIVATE.resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or resolved == ROOT.resolve():
        raise ValueError('Private output resolves outside the workspace')
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


@contextmanager
def exclusive_session(root):
    lock = root/'.reader.lock'
    try:
        handle = lock.open('x', encoding='utf-8')
    except FileExistsError:
        raise RuntimeError('A reader lock exists. Do not start another session; inspect the previous run first.') from None
    try:
        handle.write(str(os.getpid()))
        handle.flush()
        yield
    finally:
        handle.close()
        lock.unlink()


class SessionFiles:
    def __init__(self, root, kind):
        name = kind+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
        self.path = root/name
        self.path.mkdir()
        self.manifest = dict(kind=kind, started_utc=datetime.now(timezone.utc).isoformat(),
                             firmware_user_report='2.01', model='ILCE-7CM2',
                             status='started', files=[], exit_verified=False)
        self.save()

    def event(self, name, **fields):
        record = dict(event=name, utc=datetime.now(timezone.utc).isoformat(), **fields)
        with (self.path/'events.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps(record)+'\n')

    def save(self):
        temp = self.path/'manifest.json.partial'
        temp.write_text(json.dumps(self.manifest, indent=2)+'\n', encoding='utf-8')
        temp.replace(self.path/'manifest.json')

    def snapshot(self, name, raw):
        destination = self.path/(name+'.bin')
        with destination.open('xb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        self.manifest['files'].append(dict(name=name, path=destination.name,
                                          bytes=len(raw), sha256=sha(raw)))
        self.save()


class DriverUnavailable(RuntimeError):
    pass


class UsbRaw:
    """Thin Windows USB adapter. No set_configuration, reset or clear_halt calls."""
    def __init__(self, device, util, clock=time.monotonic):
        self.dev, self.util, self.clock = device, util, clock
        self.deadline = clock()+10
        interface = device.get_active_configuration()[(0, 0)]
        incoming = [e.bEndpointAddress for e in interface if e.bmAttributes & 3 == 2 and e.bEndpointAddress & 128]
        outgoing = [e.bEndpointAddress for e in interface if e.bmAttributes & 3 == 2 and not e.bEndpointAddress & 128]
        if not incoming or not outgoing:
            raise DriverUnavailable('Required bulk endpoints missing')
        # Same interface 0 / first bulk endpoint pair as the pinned transport.
        self.ep_in, self.ep_out = incoming[0], outgoing[0]
        # Descriptor reads alone do not establish usable Windows driver access.
        # Claim before sending any service-start/authentication request.
        util.claim_interface(device, 0)

    def begin(self, seconds):
        self.deadline = self.clock()+seconds

    def timeout(self):
        left = int((self.deadline-self.clock())*1000)
        if left <= 0:
            raise TimeoutError('USB operation deadline reached')
        return min(left, 10000)

    def write(self, data):
        written = self.dev.write(self.ep_out, data, timeout=self.timeout())
        if written != len(data):
            raise OSError('Short USB request write')

    def read(self, length):
        return bytes(self.dev.read(self.ep_in, length, timeout=self.timeout()))

    def control(self, request):
        if request not in (START, STOP):
            raise PolicyError('Unapproved USB control request')
        result = self.dev.ctrl_transfer(*request, b'', timeout=self.timeout())
        if result not in (0, None):
            raise OSError('Unexpected control-transfer result')

    def close(self):
        self.util.dispose_resources(self.dev)


def host_devices():
    executable = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(executable), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                             '-File', str(ROOT/'app/a7c2_usb_status.ps1'), '-AllowDeviceQuery', '-AsJson'],
                            capture_output=True, text=True, encoding='utf-8', timeout=20, check=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    rows = json.loads(result.stdout.lstrip('\ufeff'))
    if not isinstance(rows, list):
        raise ValueError('Unexpected Windows inventory result')
    return rows


class UsbSystem:
    def __init__(self, event, announce=print, clock=time.monotonic, sleep=time.sleep):
        # This constructor is called ONLY after explicit live CLI gates and
        # preflight. Importing this module or running tests does not reach it.
        import usb.core
        import usb.util
        import usb.backend.libusb1
        import libusb_package
        self.core, self.util = usb.core, usb.util
        self.backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        if self.backend is None:
            raise DriverUnavailable('libusb backend could not be loaded')
        self.event, self.announce, self.clock, self.sleep = event, announce, clock, sleep

    def inventory(self):
        rows = host_devices()
        if len(rows) > 1:
            raise RuntimeError('More than one Sony USB parent present; connect only this camera')
        return rows

    def _open(self, pid, require_model=False):
        devices = list(self.core.find(find_all=True, idVendor=0x054c, idProduct=pid, backend=self.backend))
        if len(devices) != 1:
            raise DriverUnavailable('Expected one accessible USB device; check the driver')
        device = devices[0]
        try:
            if require_model:
                model = self.util.get_string(device, device.iProduct) if device.iProduct else None
                if model != 'ILCE-7CM2':
                    raise ValueError('USB product string is not ILCE-7CM2')
            return UsbRaw(device, self.util)
        except BaseException:
            self.util.dispose_resources(device)
            raise

    def normal(self):
        rows = self.inventory()
        self.event('normal_inventory', devices=rows)
        if len(rows) != 1 or rows[0]['pid'] != '0e8a':
            raise RuntimeError('Expected normal 054C:0E8A. Select Image Transfer (MSC); no authentication sent.')
        try:
            return self._open(NORMAL_PID, require_model=True)
        except (OSError, NotImplementedError) as exc:
            raise DriverUnavailable('Normal USB interface inaccessible. Check 054C:0E8A driver; no authentication sent.') from exc

    def service(self):
        deadline, driver_deadline, announced = self.clock()+30, None, False
        while self.clock() < (driver_deadline if driver_deadline is not None else deadline):
            rows = self.inventory()
            if rows and rows[0]['pid'] == '0336':
                if driver_deadline is None:
                    driver_deadline = self.clock()+180
                    self.event('service_identity_seen', devices=rows)
                try:
                    return self._open(SERVICE_PID)
                except (OSError, NotImplementedError, DriverUnavailable):
                    if not announced:
                        self.announce('SERVICE_DRIVER_WAIT: keep this terminal running. In Zadig, select ONLY '
                                      'Sony USB Device 054C:0336 and install WinUSB if needed. '
                                      'Reader resumes automatically when accessible (up to 180 seconds).')
                        self.event('service_driver_wait')
                        announced = True
            elif driver_deadline is not None:
                raise RuntimeError('Service identity disappeared during driver setup; no re-authentication attempted')
            elif rows and rows[0]['pid'] != '0e8a':
                raise RuntimeError('Unexpected Sony identity during transition; stopped')
            self.sleep(1)
        raise DriverUnavailable('Service connection not accessible within the deadline; no automatic retry')

    def verify_normal_return(self):
        deadline = self.clock()+30
        while self.clock() < deadline:
            rows = self.inventory()
            if len(rows) == 1 and rows[0]['pid'] == '0e8a':
                return True
            self.sleep(1)
        return False

    def settle_service(self):
        # The pinned transport also waits two seconds after obtaining 0336.
        self.sleep(2)


def collect(system, files, keys, announce=print):
    """Run one connection attempt. Injection enables full offline fault tests."""
    raw, service, error = None, None, None
    snapshots = {}
    try:
        files.event('normal_open')
        raw = system.normal()
        normal = Protocol(raw, NORMAL_PID, keys, files.event)
        announce('NORMAL_AUTH: requesting service access once.')
        normal.authenticate()
        raw.close()
        raw = None
        files.event('normal_authenticated')
        announce('WAIT_SERVICE: waiting for 054C:0336; do not select another camera mode.')
        raw = system.service()
        system.settle_service()
        service = Protocol(raw, SERVICE_PID, keys, files.event)
        service.authenticate()
        files.event('service_authenticated')
        identity = None
        for name, memory in VIEWS:
            announce('READ: '+name)
            data = service.snapshot(memory)
            files.snapshot(name, data)  # Preserve complete raw reply even if parsing fails.
            blocks = parse_snapshot(data)
            current_identity = identity_digest(blocks)
            if identity is not None and current_identity != identity:
                raise BackupError('Body identity changed between backup views')
            identity = current_identity
            snapshots[name] = data
            files.event('snapshot_validated', snapshot=name, bytes=len(data), sha256=sha(data))
        files.manifest['status'] = 'captured'
    except BaseException as exc:
        error = exc
        files.manifest['status'] = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed'
        # Full diagnostic stays private, not in a published artifact.
        files.manifest['error'] = type(exc).__name__+': '+str(exc)
    finally:
        # File/logging failures must not prevent the normal exit attempt when
        # the protocol is known to be authenticated and healthy.
        exit_attempted = False
        if service is not None and service.healthy and service.policy.state == 'ready':
            exit_attempted = True
            try:
                service.stop()
            except BaseException as exc:
                files.manifest['exit_transfer_error'] = type(exc).__name__
        if raw is not None:
            try:
                raw.close()
            except BaseException as exc:
                files.manifest['close_error'] = type(exc).__name__
        if exit_attempted:
            try:
                files.manifest['exit_verified'] = system.verify_normal_return()
            except BaseException as exc:
                files.manifest['exit_verification_error'] = type(exc).__name__
        files.manifest['exit_attempted'] = exit_attempted
        files.save()
    if files.manifest['status'] == 'captured':
        analysis = compare_snapshots(snapshots)
        (files.path/'analysis.json').write_text(json.dumps(analysis, indent=2)+'\n', encoding='utf-8')
        announce('CAPTURE_COMPLETE: four structurally valid snapshots saved privately.')
        announce('NORMAL_USB_RETURN: '+str(files.manifest['exit_verified']))
        announce('SELECTED_RECORDS_STABLE_AND_PRESENT: '+str(analysis['research_ready']))
        return 0 if files.manifest['exit_verified'] else 2
    announce('STOPPED: '+type(error).__name__+'. See the private manifest; do not rerun collect automatically.')
    if not files.manifest['exit_verified']:
        announce('Normal USB return is unverified. No rescue, reset or re-authentication was attempted.')
    return 2


def analyze(path):
    root = private_root()
    folder = Path(path).resolve()
    if not folder.is_relative_to(root) or folder == root:
        raise ValueError('Analyze only a session under data/private/readonly')
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    snapshots = {}
    for entry in manifest['files']:
        name = entry['name']
        if name not in dict(VIEWS) or entry['path'] != name+'.bin' or name in snapshots:
            raise ValueError('Unexpected/duplicate snapshot entry')
        file = (folder/entry['path']).resolve()
        if not file.is_relative_to(folder) or file.stat().st_size > MAX_SNAPSHOT:
            raise ValueError('Snapshot path or size invalid')
        data = file.read_bytes()
        if len(data) != entry['bytes'] or sha(data) != entry['sha256']:
            raise ValueError('Saved snapshot differs from acquisition manifest')
        snapshots[name] = data
    result = compare_snapshots(snapshots)
    (folder/'analysis.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    # Deliberately do not print per-body coefficients or serials to shared logs.
    print(json.dumps(dict(research_ready=result['research_ready'], repeat_stable=result['repeat_stable'],
                          stored_equals_memory=result['stored_equals_memory'],
                          coefficient_states={k: 'unavailable' if v is None else 'all_zero' if not any(v) else 'nonzero'
                                              for k, v in result['coefficients'].items()},
                          exit_verified=manifest['exit_verified'], private_report=str(folder/'analysis.json')), indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('preflight', help='Offline file/version checks; no USB imports or enumeration')
    for name in ('probe', 'collect'):
        command = sub.add_parser(name, help='LIVE: '+('normal descriptors only; no authentication' if name == 'probe' else 'service entry, four backup reads, normal exit'))
        command.add_argument('--allow-camera-read', action='store_true', required=True)
        command.add_argument('--firmware', choices=['2.01'], required=True)
    analysis = sub.add_parser('analyze', help='Offline analysis of already saved private snapshots')
    selection = analysis.add_mutually_exclusive_group(required=True)
    selection.add_argument('--session', type=Path)
    selection.add_argument('--latest', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'preflight':
        print(json.dumps(preflight(), indent=2))
        return 0
    if args.command == 'analyze':
        if args.latest:
            sessions = sorted(p for p in private_root().glob('collect-*') if p.is_dir())
            if not sessions:
                raise ValueError('No saved collection session')
            args.session = sessions[-1]
        analyze(args.session)
        return 0
    # No USB imports, enumeration or handles before BOTH live flags + preflight.
    if not args.allow_camera_read or args.firmware != '2.01':
        raise ValueError('Explicit live flags required')
    preflight()
    root = private_root()
    if shutil.disk_usage(root).free < 128*1024*1024:
        raise ValueError('At least 128 MiB free space required before connection')
    with exclusive_session(root):
        files = SessionFiles(root, args.command)
        files.manifest['reader_files'] = json.loads((ROOT/'integrity/transport-review.json').read_text())['reviewed_files']
        files.save()
        print('Private session: '+str(files.path), flush=True)
        try:
            system = UsbSystem(files.event, lambda message: print(message, flush=True))
        except BaseException as exc:
            files.manifest.update(status='failed-before-session', error=type(exc).__name__+': '+str(exc))
            files.save()
            raise
        if args.command == 'collect':
            return collect(system, files, load_keys(), lambda message: print(message, flush=True))
        raw = None
        try:
            raw = system.normal()
            files.manifest['status'] = 'probe-passed'
            print('PROBE_OK: ILCE-7CM2 normal interface accessible. No service authentication sent.')
            return 0
        except BaseException as exc:
            files.manifest['status'] = 'failed'
            files.manifest['error'] = type(exc).__name__+': '+str(exc)
            raise
        finally:
            if raw is not None:
                raw.close()
            files.save()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print('STOPPED: '+type(exc).__name__+': '+str(exc), file=sys.stderr)
        raise SystemExit(2)
