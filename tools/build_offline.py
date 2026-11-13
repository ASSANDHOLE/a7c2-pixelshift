"""Reproduce exact C2 2.01 AP/CP candidates and their inverse using local inputs.

No USB, device discovery, service credentials, download or deployment operation.
Generated files contain supplied coefficients and must stay outside the public tree.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / 'profiles/ilce7cm2-2.01.json'
GETTER, PACKET = 0xaa74ea, 0x418be0


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def profile():
    p = json.loads(PROFILE_FILE.read_text(encoding='utf-8'))
    if (p['schema'], p['model'], p['firmware']) != (1, 'ILCE-7CM2', '2.01'):
        raise ValueError('Unexpected profile identity')
    return p


def coefficients(value):
    if not isinstance(value, list) or len(value) != 3 or any(type(v) is not int or not 1 <= v <= 255 for v in value):
        raise ValueError('Supply three explicitly reviewed nonzero integer coefficients in 1..255; no defaults')
    return value


def movw(register, value):
    if not 0 <= register < 15 or not 0 <= value <= 65535:
        raise ValueError('MOVW operands')
    return struct.pack('<HH', 0xf240 | ((value >> 12) & 15) | (((value >> 11) & 1) << 10),
                       (((value >> 8) & 7) << 12) | (register << 8) | (value & 255))


def bl(at, target):
    delta = target - at - 4
    if delta % 2 or not -(1 << 24) <= delta < (1 << 24):
        raise ValueError('Thumb BL range')
    n = delta & 0x1ffffff
    sign, i1, i2 = (n >> 24) & 1, (n >> 23) & 1, (n >> 22) & 1
    return struct.pack('<HH', 0xf000 | (sign << 10) | ((n >> 12) & 0x3ff),
                       0xd000 | ((1 ^ i1 ^ sign) << 13) | ((1 ^ i2 ^ sign) << 11) | ((n >> 1) & 0x7ff))


def cb(at, target, register=0, nonzero=False):
    delta = target - at - 4
    if delta % 2 or not 0 <= delta <= 126 or not 0 <= register < 8:
        raise ValueError('Thumb CBZ/CBNZ range')
    n = delta // 2
    return struct.pack('<H', (0xb900 if nonzero else 0xb100) | ((n & 32) << 4) | ((n & 31) << 3) | register)


def pair_getter():
    # Existing reviewed generator: snapshot the pair from one PXS-state read.
    b = bytearray.fromhex('16b5')
    b += bl(GETTER + len(b), 0xaa975c)
    b += cb(GETTER + len(b), GETTER + 14)
    b += movw(0, 0x103) + bytes.fromhex('16bd')
    b += bl(GETTER + len(b), 0xaa7112)
    b += bytes.fromhex('90f83d40 90f83e10')
    literal, pc = GETTER + 42, (GETTER + len(b) + 4) & ~3
    b += struct.pack('<H', 0x4a00 + (literal - pc) // 4)
    b += cb(GETTER + len(b), GETTER + 32, 4, True)
    b += bytes.fromhex('d478')
    b += cb(GETTER + len(b), GETTER + 36, 1, True)
    b += bytes.fromhex('1178 44ea0120 16bd')
    if len(b) != 42:
        raise ValueError('Pair getter encoding')
    b += struct.pack('<I', 0x1b1afa7)
    return bytes(b) + bytes.fromhex('00bf') * ((68 - len(b)) // 2)


def packet_builder():
    b = bl(PACKET, GETTER) + bytes.fromhex('0446') + bl(PACKET + 6, 0xaa833a)
    return b + bytes.fromhex('c473 4fea1424 0474') + bytes.fromhex('00bf') * 3


def windows(component, values):
    result = []
    for item in component['spans']:
        row = {k: v for k, v in item.items() if k != 'replacement'}
        if 'replacement' in item:
            rule = item['replacement']
            kind = rule['kind']
            if kind == 'coefficient_movw':
                after = movw(rule['register'], values[rule['coefficient_index']])
            elif kind == 'pair_getter':
                after = pair_getter()
            elif kind == 'packet_builder':
                after = packet_builder()
            elif kind == 'profile6':
                after = bytes.fromhex('0620')
            else:
                raise ValueError('Unknown fixed patch encoder')
            row['after_hex'] = after.hex()
        result.append(row)
    return result


def transform(data, spans, reverse=False):
    output = bytearray(data)
    end = 0
    for span in spans:
        offset = span['offset']
        before = bytes.fromhex(span['after_hex'] if reverse else span['before_hex'])
        after = bytes.fromhex(span['before_hex'] if reverse else span['after_hex'])
        if type(offset) is not int or offset < end or not before or len(before) != len(after) or offset + len(before) > len(data):
            raise ValueError('Invalid or overlapping patch window')
        if output[offset:offset + len(before)] != before:
            raise ValueError('Unexpected bytes at a fixed patch window')
        output[offset:offset + len(before)] = after
        end = offset + len(before)
    return bytes(output)


def external_output(path):
    path = Path(path).resolve()
    if path == ROOT or path.is_relative_to(ROOT):
        raise ValueError('Keep generated private files outside the public repository')
    return path


def generate_header(manifest, p, folder, output, fixture=False):
    lines = ['struct Loaded{u64 rva,stock,candidate;u32 n,pointer;};']
    entries, data_files = [], []
    for chip, c in enumerate(manifest['components']):
        data = bytearray([0x55] * (8192 if chip == 0 else 4096)) if fixture else bytearray((output / c['stock_source']).read_bytes())
        for j, span in enumerate(c['spans']):
            offset = 256 + j * 128 if fixture else span['offset']
            before, after = bytes.fromhex(span['before_hex']), bytes.fromhex(span['after_hex'])
            data[offset:offset + len(before)] = before
            key = f'w{chip}_{j}'
            for suffix, value in [('a', before), ('b', after)]:
                lines.append(f'static const u8 {key}_{suffix}[]={{' + ','.join(map(str, value)) + '};')
            entries.append((chip, offset, len(before), key))
        data_files.append(data)
    fields, cow = p['loaded_fields'], p['cow_fields']
    lines += [
        'static const struct Window windows[]={' + ','.join('{%dULL,%d,%d,%s_a,%s_b}' % (o, n, c, k, k) for c, o, n, k in entries) + '};',
        f'static const u32 window_count={len(entries)};',
        'static const u64 file_sizes[]={' + ','.join(str(len(d)) + 'ULL' for d in data_files) + '};',
        'static const struct Loaded loaded_fields[]={' + ','.join('{%dULL,%dULL,%dULL,%d,%d}' % tuple(f) for f in fields) + '};',
        f'static const u32 loaded_count={len(fields)};',
        'static const struct Cow{u64 rva,addend;} cow_fields[]={' + ','.join('{%dULL,%dULL}' % tuple(f) for f in cow) + '};',
        f'static const u32 cow_count={len(cow)};']
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'persistent_manifest.h').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    if fixture:
        for chip, data in enumerate(data_files):
            (folder / f'stock-{chip}.bin').write_bytes(data)
            candidate = bytearray(data)
            for c, offset, size, key in entries:
                if c == chip:
                    j = int(key.split('_')[1])
                    candidate[offset:offset + size] = bytes.fromhex(manifest['components'][chip]['spans'][j]['after_hex'])
            (folder / f'candidate-{chip}.bin').write_bytes(candidate)
        save_json(folder / 'fixture.json', dict(fields=fields + [[a, b, b, 8, 1] for a, b in cow], cow=cow,
                   windows=[dict(chip=c, offset=o, length=n) for c, o, n, _ in entries]))


def build(inputs, destination):
    inputs = Path(inputs).resolve()
    output = external_output(destination)
    if output.exists():
        raise ValueError('Output already exists; choose a new private directory')
    config = json.loads(inputs.read_text(encoding='utf-8-sig'))
    required = {'schema', 'model', 'firmware', 'ap_file', 'cp_file', 'coefficients'}
    if set(config) != required or type(config['schema']) is not int or (config['schema'], config['model'], config['firmware']) != (1, 'ILCE-7CM2', '2.01'):
        raise ValueError('Input schema/model/firmware differs from the supported specification')
    if any(not isinstance(config[k], str) or not config[k].strip() for k in ['ap_file', 'cp_file']):
        raise ValueError('AP/CP paths must be nonempty strings')
    values, p = coefficients(config['coefficients']), profile()
    prepared = []
    for c in p['components']:
        name = c['name']
        path = (inputs.parent / config[name.lower() + '_file']).resolve()
        original = path.read_bytes()
        if len(original) != c['bytes'] or digest(original) != c['stock_sha256']:
            raise ValueError(name + ' must be the exact stock 2.01 component; no best-effort offset matching')
        spans = windows(c, values)
        candidate = transform(original, spans)
        reversed_data = transform(candidate, spans, True)
        if reversed_data != original:
            raise ValueError('Complete inverse mismatch')
        changed = sum(sum(a != b for a, b in zip(bytes.fromhex(s['before_hex']), bytes.fromhex(s['after_hex']))) for s in spans)
        row = dict(name=name, bytes=len(original), stock_source=name + '.stock.bin', candidate_path=name + '.candidate.bin',
                   reversed_path=name + '.reversed.bin', stock_sha256=digest(original), candidate_sha256=digest(candidate),
                   changed_bytes=changed, spans=spans, inverse_restores_complete_original=True)
        prepared.append((row, original, candidate, reversed_data))
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema=1, profile=p['profile'], model=p['model'], firmware=p['firmware'], public_version='v1',
                    coefficients=values, camera_access=False, body_binding=False, source_input_sha256=file_hash(inputs),
                    profile_sha256=file_hash(PROFILE_FILE), status='offline-artifacts-only-not-authorized-for-camera',
                    components=[x[0] for x in prepared])
    for row, original, candidate, reversed_data in prepared:
        for key, data in [('stock_source', original), ('candidate_path', candidate), ('reversed_path', reversed_data)]:
            (output / row[key]).write_bytes(data)
    generate_header(manifest, p, output / 'writer', output)
    generate_header(manifest, p, output / 'writer/fixture', output, True)
    (output / 'native').mkdir()
    shutil.copy2(ROOT / 'src/v1/offline/native/install_writer.c', output / 'native/persistent_writer.c')
    for name in ['a7c2_linux_abi.h', 'persistent_maps.inc', 'sha256.h']:
        for target in [output / 'writer', output / 'writer/fixture']:
            shutil.copy2(ROOT / 'src/v1/native' / name, target / name)
    shutil.copy2(ROOT / 'tests/support/persistent_test_abi.h', output / 'writer/fixture/persistent_test_abi.h')
    manifest['artifact_files'] = [dict(path=f.relative_to(output).as_posix(), bytes=f.stat().st_size, sha256=file_hash(f))
                                  for f in sorted(output.rglob('*')) if f.is_file()]
    save_json(output / 'manifest.json', manifest)
    verify(output)
    print('OFFLINE_BUILD_OK: AP/CP candidates, complete inverse, manifest, native header and synthetic fixtures; no camera access.')
    return output


def verify(output):
    output = external_output(output)
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    p, values = profile(), coefficients(manifest['coefficients'])
    if manifest['profile_sha256'] != file_hash(PROFILE_FILE) or manifest['body_binding'] is not False:
        raise ValueError('Profile/binding declaration mismatch')
    if [c['name'] for c in manifest['components']] != ['AP', 'CP']:
        raise ValueError('Component list differs')
    for c, spec in zip(manifest['components'], p['components']):
        name = c['name']
        for key, suffix in [('stock_source', '.stock.bin'), ('candidate_path', '.candidate.bin'), ('reversed_path', '.reversed.bin')]:
            if c[key] != name + suffix:
                raise ValueError('Unexpected component artifact path')
        original = (output / c['stock_source']).read_bytes()
        if len(original) != spec['bytes'] or digest(original) != spec['stock_sha256']:
            raise ValueError('Original component hash differs')
        spans = windows(spec, values)
        if spans != c['spans']:
            raise ValueError('Generated windows differ from the fixed profile')
        candidate = transform(original, spans)
        if (output / c['candidate_path']).read_bytes() != candidate or digest(candidate) != c['candidate_sha256']:
            raise ValueError('Candidate differs from deterministic transformation')
        if (output / c['reversed_path']).read_bytes() != original or transform(candidate, spans, True) != original:
            raise ValueError('Complete inverse differs')
    for row in manifest['artifact_files']:
        path = (output / row['path']).resolve()
        if not path.is_relative_to(output) or path.is_symlink() or path.stat().st_size != row['bytes'] or file_hash(path) != row['sha256']:
            raise ValueError('Generated artifact integrity differs: ' + row['path'])
    return manifest


def compile_helper(output, zig):
    output = external_output(output)
    verify(output)
    zig = Path(zig).resolve()
    version = subprocess.run([str(zig), 'version'], capture_output=True, text=True, check=True).stdout.strip()
    if version != '0.13.0':
        raise ValueError('This recipe was checked with Zig 0.13.0')
    build_dir, source = output / 'writer', output / 'native/persistent_writer.c'
    if any((build_dir / f).exists() for f in ['persistent-writer.so', 'persistent-test.dll']):
        raise ValueError('Compiled output already exists; use a fresh artifact directory')
    env = os.environ.copy()
    # Explicit, short local cache paths avoid Zig/Windows temporary-path limits.
    global_cache, local_cache = output / '.zig/g', output / '.zig/l'
    for directory in [global_cache, local_cache]:
        directory.mkdir(parents=True, exist_ok=True)
    env.update(ZIG_GLOBAL_CACHE_DIR=str(global_cache), ZIG_LOCAL_CACHE_DIR=str(local_cache))
    common = [str(zig), 'cc', '-shared', '-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-g0']
    headers = zig.parent / 'lib/libc/include'
    commands = [common + ['-target', 'aarch64-linux-gnu', '-fPIC', '-nostdlib', '-Wl,--no-undefined', '-Wl,-Bsymbolic',
                '-Wl,-z,noexecstack', '-isystem', str(headers / 'aarch64-linux-any'), '-isystem', str(headers / 'any-linux-any'),
                '-I', str(build_dir), str(source), '-o', str(build_dir / 'persistent-writer.so')],
                common + ['-target', 'x86_64-windows-gnu', '-DHOST_TEST', '-I', str(build_dir / 'fixture'),
                str(source), '-o', str(build_dir / 'persistent-test.dll')]]
    for command in commands:
        completed = subprocess.run(command, env=env, capture_output=True, text=True, timeout=180)
        if completed.returncode:
            raise RuntimeError(completed.stderr[-5000:])
    from elftools.elf.elffile import ELFFile
    with (build_dir / 'persistent-writer.so').open('rb') as stream:
        elf = ELFFile(stream)
        if elf['e_machine'] != 'EM_AARCH64' or elf['e_type'] != 'ET_DYN':
            raise ValueError('Unexpected native target')
        if any(t.entry.d_tag == 'DT_NEEDED' for t in elf.get_section_by_name('.dynamic').iter_tags()):
            raise ValueError('Native helper has an external library dependency')
        if any(s.name and s['st_shndx'] == 'SHN_UNDEF' for s in elf.get_section_by_name('.dynsym').iter_symbols()):
            raise ValueError('Native helper has an unresolved symbol')
    if (build_dir / 'persistent-writer.so').stat().st_size >= 65536:
        raise ValueError('Native helper exceeds the reviewed size bound')
    save_json(build_dir / 'build.json', dict(status='compiled-offline-awaiting-tests', camera_access=False,
              compiler_version=version, compiler_sha256=file_hash(zig), manifest_sha256=file_hash(output / 'manifest.json'),
              binaries={name: file_hash(build_dir / name) for name in ['persistent-writer.so', 'persistent-test.dll']}))
    print('OFFLINE_COMPILE_OK: AArch64 helper and Windows x64 syscall fixture; neither deployed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('--inputs', type=Path, required=True); b.add_argument('--output', type=Path, required=True)
    v = sub.add_parser('verify'); v.add_argument('--output', type=Path, required=True)
    c = sub.add_parser('compile'); c.add_argument('--output', type=Path, required=True); c.add_argument('--zig', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.inputs, args.output)
    elif args.command == 'verify':
        verify(args.output); print('OFFLINE_VERIFY_OK; complete candidates/inverses match; no camera access.')
    else:
        compile_helper(args.output, args.zig)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit('STOPPED (offline): ' + str(error))
