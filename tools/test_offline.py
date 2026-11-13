"""Run existing native/ARM64 failure tests with generated local artifacts only."""
import argparse
import importlib
import json
from pathlib import Path
import re
import shutil
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_offline as builder


def module(name, **values):
    item = types.ModuleType(name)
    item.__dict__.update(values)
    sys.modules[name] = item


def run(output):
    if not __debug__:
        raise ValueError('Run the offline tests without Python -O')
    if sys.platform != 'win32':
        raise ValueError('The compiled syscall fixture is currently tested on Windows x64 only')
    output = builder.external_output(output)
    manifest = builder.verify(output)
    report = json.loads((output / 'writer/build.json').read_text(encoding='utf-8'))
    if report['manifest_sha256'] != builder.file_hash(output / 'manifest.json'):
        raise ValueError('Compiled helper belongs to a different manifest')
    for name, expected in report['binaries'].items():
        if builder.file_hash(output / 'writer' / name) != expected:
            raise ValueError('Compiled binary changed')
    support = builder.ROOT / 'tests/support'
    tests = output / 'tests'
    results = tests / 'results'
    results.mkdir(parents=True, exist_ok=True)
    for name in ['test_persistent_writer_native.py', 'test_persistent_writer_arm.py']:
        shutil.copy2(support / name, tests / name)
    abi_path = output / 'writer/fixture/persistent_test_abi.h'
    abi = {name: int(value) for name, value in re.findall(r'^#define (\w+) \((-?\d+)\)$', abi_path.read_text(), re.M)}
    if (abi['O_DIRECTORY'], abi['O_DIRECT'], abi['O_NOFOLLOW']) != (0x4000, 0x10000, 0x8000):
        raise ValueError('Target ABI constants differ')
    module('acquire', ROOT=output, sha256=builder.file_hash)
    module('prepare_persistent_writer', BUILD=output / 'writer', target_flags=lambda: (abi, [dict(path='writer/fixture/persistent_test_abi.h', sha256=builder.file_hash(abi_path))]))
    module('persistent_pixelshift_v1', OUT=output, digest=builder.digest)
    module('test_paths', TEST_OUT=results)
    # The support protocol has full-install bounds; the review CP-only updater
    # intentionally has narrower limits and must not be substituted here.
    sys.path[:0] = [str(tests), str(support), str(builder.ROOT / 'src/v1/host')]
    native = importlib.import_module('test_persistent_writer_native')
    native.main()
    arm = importlib.import_module('test_persistent_writer_arm')
    arm.main()
    if any(name == 'usb' or name.startswith('usb.') for name in sys.modules):
        raise ValueError('Unexpected USB module import in offline tests')
    native_report = json.loads((results / 'native-tests.json').read_text())
    arm_report = json.loads((results / 'arm-tests.json').read_text())
    summary = dict(status='passed-offline', camera_access=False, USB_imported=False,
                   native_fault_cases=native_report['count'], AArch64_helper_cases=len(arm_report['cases']),
                   manifest_sha256=builder.file_hash(output / 'manifest.json'),
                   helper_sha256=report['binaries']['persistent-writer.so'],
                   coefficients_published=False,
                   limits=['Simulated Linux syscalls and local files; no physical USB, storage, cold-boot or power-loss test.',
                           'No body-binding/session package or deployment authorization is created.'])
    builder.save_json(results / 'summary.json', summary)
    print('OFFLINE_HELPER_TESTS_OK:', summary['native_fault_cases'], 'native cases,', summary['AArch64_helper_cases'], 'ARM64 cases; no camera access.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
