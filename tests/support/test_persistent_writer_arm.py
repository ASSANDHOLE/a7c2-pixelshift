"""Execute the actual AArch64 release binary under Unicorn with fake syscalls."""
import ctypes,io,json
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_INTR
import unicorn.arm64_const as reg
from acquire import ROOT,sha256
from test_paths import TEST_OUT
from prepare_persistent_writer import BUILD
from persistent_pixelshift_v1 import OUT
from persistent_writer_protocol import RESULT,parse
from test_persistent_writer_native import OS,AP,CP

BIAS=0x10000000;STACK=0x20000000;STOP=0x30000000

def execute(action,initial='stock',binary_path=None,expected_status=None,**fault):
    os=OS(action,initial,**fault);manifest=json.loads((OUT/'manifest.json').read_text());os.fixture['windows']=[]
    for chip,row in enumerate(manifest['components']):
        os.files[(AP,CP)[chip]]=bytearray((ROOT/row['stock_source' if initial=='stock' else 'candidate_path']).read_bytes())
        os.fixture['windows'] += [dict(chip=chip,offset=w['offset'],length=len(bytes.fromhex(w['before_hex']))) for w in row['spans']]
    raw=(binary_path or BUILD/'persistent-writer.so').read_bytes();elf=ELFFile(io.BytesIO(raw));u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    segments=[p for p in elf.iter_segments() if p['p_type']=='PT_LOAD'];end=max(p['p_vaddr']+p['p_memsz'] for p in segments)
    u.mem_map(BIAS,(end+4095)&~4095)
    for p in segments:u.mem_write(BIAS+p['p_vaddr'],p.data())
    for r in elf.get_section_by_name('.rela.dyn').iter_relocations():
        assert r['r_info_type']==1027;u.mem_write(BIAS+r['r_offset'],(BIAS+r['r_addend']).to_bytes(8,'little'))
    init=next(s['st_value'] for s in elf.get_section_by_name('.dynsym').iter_symbols() if s.name=='_init')
    u.mem_map(STACK,0x40000);u.mem_map(STOP,4096)
    def string(at):
        out=bytearray()
        for i in range(1024):
            b=u.mem_read(at+i,1)
            if not b[0]:return bytes(out)
            out+=b
        raise AssertionError('Unterminated syscall path')
    errors=[]
    def interrupt(uc,kind,user):
        try:
            assert kind==2;no=uc.reg_read(reg.UC_ARM64_REG_X8);args=[uc.reg_read(reg.UC_ARM64_REG_X0+i) for i in range(6)]
            args=[v-(1<<64) if v>>63 else v for v in args];original=args.copy();buffers=[];output=None
            if no in (56,35,40):
                assert args[1]>0;buf=ctypes.create_string_buffer(string(args[1]));buffers.append(buf);args[1]=ctypes.addressof(buf)
            elif no in (63,67,80):
                n=128 if no==80 else args[2];assert 0<=n<=524288;buf=ctypes.create_string_buffer(n);buffers.append(buf);args[1]=ctypes.addressof(buf);output=(original[1],buf,n)
            elif no in (64,68):
                assert 0<=args[2]<=65536;buf=ctypes.create_string_buffer(bytes(uc.mem_read(args[1],args[2])));buffers.append(buf);args[1]=ctypes.addressof(buf)
            value=os.dispatch(no,*args)
            if output and value>=0:
                address,buf,n=output;uc.mem_write(address,buf.raw[:n if no==80 else value])
            uc.reg_write(reg.UC_ARM64_REG_X0,value&0xffffffffffffffff)
        except BaseException as ex:errors.append(repr(ex));uc.emu_stop()
    u.hook_add(UC_HOOK_INTR,interrupt);u.reg_write(reg.UC_ARM64_REG_SP,STACK+0x3ff00);u.reg_write(reg.UC_ARM64_REG_X30,STOP)
    u.emu_start(BIAS+init,STOP,count=30_000_000,timeout=30_000_000)
    assert not errors and not os.errors,(errors,os.errors)
    assert u.reg_read(reg.UC_ARM64_REG_PC)==STOP,'Execution boundary not reached'
    report=parse(bytes(os.files[RESULT]),os.req)
    target='stock' if action==2 or fault else 'candidate' if action==1 else initial
    for chip,row in enumerate(manifest['components']):assert os.files[(AP,CP)[chip]]==(ROOT/row['stock_source' if target=='stock' else 'candidate_path']).read_bytes()
    if expected_status is None:assert (report['status']!=0)==bool(fault) and not report['rollback']
    else:assert report['status']==expected_status and not report['mutated'] and not report['writes']
    return dict(action=action,initial=initial,fault=fault,status=report['status'],cleanup=report['cleanup'],cleanup_calls=report.get('cleanup_calls'),open_errors=os.open_errors,
        writes=report['writes'],syscalls=len(os.syscalls),complete_file_comparison=True)

def main():
    cases=[]
    archived=BUILD/'history/20261102-before-arm64-flag-fix/persistent-writer.so'
    if archived.exists():
        regression=execute(0,binary_path=archived,expected_status=-121)
        assert regression['cleanup']==-22 and regression['open_errors']==[dict(path='/tmp/jiritsu',flags=0x10000,errno=-22)]
        cases.append(dict(case='archived-binary-reproduces-camera-EINVAL',binary_sha256=sha256(archived),**regression))
        cases.append(dict(case='new-preparation-passes-target-ABI-model',**execute(0)))
    for action,initial,fault in [(1,'stock',{}),(2,'candidate',{}),(3,'candidate',{}),(1,'stock',{'fail_write':4})]:
        cases.append(execute(action,initial,**fault));print('Passed release AArch64 case:',action,initial,fault,flush=True)
    result=dict(status='passed-offline',camera_io=False,cases=cases,binary_sha256=sha256(BUILD/'persistent-writer.so'),
        source_sha256=sha256(ROOT/'tests/test_persistent_writer_arm.py'),build_sha256=sha256(BUILD/'build.json'),
        limits=['Exact release ELF executed with simulated Linux syscalls and real candidate/original bytes; not a physical USB/storage/boot test.'])
    (TEST_OUT/'arm-tests.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
