"""Execute the writer's C logic with a simulated syscall layer; no camera IO."""
import ctypes,json,struct
from acquire import ROOT,sha256
from test_paths import TEST_OUT
from prepare_persistent_writer import BUILD,target_flags
from persistent_writer_protocol import request,parse,REQUEST,RESULT,STAGING,R

CALL=ctypes.CFUNCTYPE(ctypes.c_longlong,*([ctypes.c_longlong]*7))
AP='/usr/lib/appFw.so';CP='/cp/cpapp-b.bin';BASE=0x400000000
FIX=BUILD/'fixture'
ABI,ABI_SOURCES=target_flags()

class OS:
    def __init__(self,action=0,initial='stock',**fault):
        self.fault=fault;self.action=action;self.req=request(action);self.fixture=json.loads((FIX/'fixture.json').read_text())
        self.files={AP:bytearray((FIX/(initial+'-0.bin')).read_bytes()),CP:bytearray((FIX/(initial+'-1.bin')).read_bytes()),
            REQUEST:bytearray(self.req),STAGING:bytearray(b'fixed-helper'),'/dev/kmsg':bytearray(b'old log\n')}
        self.handles={};self.nextfd=5;self.ro=not fault.get('initial_rw',False);self.image_mode=fault.get('image_mode',2)
        self.program_writes=[];self.syscalls=[];self.errors=[];self.write_attempt=0;self.flushes=0;self.program_closes=0;self.open_errors=[]
        if fault.get('mixed'):
            target=(FIX/'candidate-1.bin').read_bytes();source=self.files[CP];changed=[i for i,(a,b) in enumerate(zip(source,target)) if a!=b]
            for i in changed[:len(changed)//2]:source[i]=target[i]
        if fault.get('outside_corrupt'):self.files[AP][0]^=1
        if fault.get('owned_corrupt'):
            w=self.fixture['windows'][0];self.files[AP][w['offset']]=0xee
        if fault.get('size_bad'):self.files[AP].append(0)
    def memory(self,offset,n):
        cells={BASE+0x5bc35b0:struct.pack('<I',self.fault.get('model',16)),BASE+0x7e6f078:struct.pack('<I',self.fault.get('mode',0)),
            BASE+0x88991a0:bytes([self.fault.get('cache',0),0x99,0x99,0x99])}
        for rva,stock,candidate,size,pointer in self.fixture['fields']:
            v=candidate if self.fault.get('loaded_candidate') else stock;v+=BASE if pointer else 0
            if self.fault.get('unrelocated') and any(rva==c[0] for c in self.fixture['cow']):v=stock
            cells[BASE+rva]=v.to_bytes(size,'little')
        for a,data in cells.items():
            if a<=offset and offset+n<=a+len(data):return data[offset-a:offset-a+n]
        raise AssertionError(('unapproved memory read',hex(offset),n))
    def data(self,path):
        flags='r--s' if self.fault.get('shared_map') else 'r--p'
        dynamic={'/proc/self/maps':f'{BASE:x}-{BASE+0x9000000:x} {flags} 00000000 00:01 42 /usr/lib/appFw.so\n'.encode(),
            '/proc/sys/kernel/random/boot_id':b'11111111-2222-4333-8444-555555555555\n',
            '/proc/mounts':('/dev/nflasha15 /usr ext2 '+('ro' if self.ro else 'rw')+',relatime 0 0\n/dev/nflasha8 /cp vfat rw,relatime 0 0\n').encode(),
            '/sys/power/image_mode':str(self.image_mode).encode()+b'\n','/sys/power/image_dev':b'*wbi4\n' if not self.fault.get('wrong_backend') else b'*other\n'}
        if path in dynamic:return dynamic[path]
        return self.files[path]
    def dispatch(self,no,a,b,c,d,e,f):
        try:return self._dispatch(no,a,b,c,d,e,f)
        except BaseException as ex:self.errors.append(repr(ex));return -999
    def _dispatch(self,no,a,b,c,d,e,f):
        self.syscalls.append(no)
        if no==175:return 1 if self.fault.get('not_root') else 0
        if no==172:return 1234
        if no==56:
            path=ctypes.string_at(b).decode();flags=c
            allowed={AP,CP,REQUEST,RESULT,STAGING,'/tmp/jiritsu','/proc/self/maps','/proc/self/mem','/proc/sys/kernel/random/boot_id','/proc/mounts','/sys/power/image_mode','/sys/power/image_dev','/sys/power/image_drop','/dev/kmsg'}
            assert path in allowed,path
            if path=='/tmp/jiritsu' and flags&ABI['O_DIRECT']:
                self.open_errors.append(dict(path=path,flags=flags,errno=-22));return -22
            if path!='/tmp/jiritsu' and flags&ABI['O_DIRECTORY']:return -20
            if path in (AP,CP) and self.fault.get('program_symlink') and flags&ABI['O_NOFOLLOW']:return -40
            if path==RESULT:
                if path in self.files:return -17
                required=ABI['O_WRONLY']|ABI['O_CREAT']|ABI['O_EXCL'];assert flags&required==required;self.files[path]=bytearray()
                self.report_nofollow=bool(flags&ABI['O_NOFOLLOW'])
            if path in (AP,CP):
                assert flags&3 in (ABI['O_RDONLY'],ABI['O_RDWR'])
                if flags&ABI['O_TRUNC']:self.files[path]=bytearray()
            fd=self.nextfd;self.nextfd+=1;self.handles[fd]=[path,0,flags];return fd
        if no==35:
            path=ctypes.string_at(b).decode();assert path in (REQUEST,STAGING)
            if self.fault.get('unlink_fail'):return -5
            if path not in self.files:return -2
            del self.files[path];return 0
        if no==57:
            path=self.handles.pop(a)[0]
            if path in (AP,CP):
                self.program_closes+=1
                if self.program_closes==self.fault.get('close_n'):return -5
            if path=='/sys/power/image_drop' and self.fault.get('drop_close_fail'):return -5
            return 0
        if no==40:
            assert ctypes.string_at(b)==b'/usr';ro=bool(d&1)
            if not ro and self.fault.get('rw_fail'):return -1
            if ro and self.fault.get('ro_fail'):return -5
            self.ro=ro;return 0
        if no==80:
            path,_,flags=self.handles[a];assert path in (AP,CP)
            raw=bytearray(128);inode=100 if path==AP else 200
            if flags&2 and self.fault.get('inode_changed'):inode+=1
            struct.pack_into('<QQIIIIQQqIIQ',raw,0,1,inode,0o100644,1,0,0,0,0,len(self.files[path]),4096,0,16)
            ctypes.memmove(b,bytes(raw),128);return 0
        if no in (63,67):
            path,pos,flags=self.handles[a];offset=pos if no==63 else d
            if path=='/proc/self/mem':raw=self.memory(offset,c)
            else:
                data=self.data(path);raw=bytes(data[offset:offset+c])
                if path=='/dev/kmsg' and not raw:return -11
            if self.fault.get('short_read'):raw=raw[:17]
            ctypes.memmove(b,raw,len(raw))
            if no==63:self.handles[a][1]+=len(raw)
            return len(raw)
        if no in (64,68):
            path,pos,flags=self.handles[a];raw=ctypes.string_at(b,c);offset=pos if no==64 else d
            if path in (AP,CP):
                assert no==68 and flags&3==ABI['O_RDWR'] and not flags&ABI['O_APPEND']
                chip=0 if path==AP else 1;assert any(w['chip']==chip and w['offset']<=offset and offset+c<=w['offset']+w['length'] for w in self.fixture['windows'])
                self.write_attempt+=1
                at=self.fault.get('fail_write')
                if at and (self.write_attempt==at or self.fault.get('sticky_write') and self.write_attempt>=at):return -5
                if self.fault.get('eintr') and self.write_attempt==1:return -4
                if self.fault.get('short_write'):raw=raw[:3]
                self.program_writes.append((path,offset,len(raw)));self.files[path][offset:offset+len(raw)]=raw;return len(raw)
            if path=='/sys/power/image_drop':
                assert raw==b'1'
                if self.fault.get('drop_write_fail'):return -5
                self.files['/dev/kmsg'].extend(b'dropped wbi\n');return 1
            if path=='/sys/power/image_mode':
                assert raw==b'0'
                if self.fault.get('mode_write_fail'):return -5
                self.image_mode=0;return 1
            assert path==RESULT and no==64
            if self.fault.get('report_short'):raw=raw[:9]
            self.files[path][offset:offset+len(raw)]=raw;self.handles[a][1]+=len(raw);return len(raw)
        if no==82:
            path=self.handles[a][0]
            if path=='/tmp/jiritsu' and self.fault.get('dir_sync_fail'):return -5
            if path in (AP,CP):
                self.flushes+=1
                if self.flushes==self.fault.get('sync_fail'):return -5
                if self.flushes==1 and self.fault.get('readback_corrupt'):
                    w=next(w for w in self.fixture['windows'] if w['chip']==(path==CP));self.files[path][w['offset']]=0xee
            return 0
        if no==62:
            path=self.handles[a][0];assert path=='/dev/kmsg' and c==2;self.handles[a][1]=len(self.files[path]);return self.handles[a][1]
        raise AssertionError(('syscall',no))
    def run(self):
        fn=CALL(self.dispatch);library.persistent_test_run(fn)
        assert not self.errors,self.errors
        return parse(bytes(self.files[RESULT]),self.req)
    def equals(self,kind):return all(self.files[path]==(FIX/f'{kind}-{i}.bin').read_bytes() for i,path in enumerate((AP,CP)))

library=ctypes.CDLL(str(BUILD/'persistent-test.dll'));library.persistent_test_run.argtypes=[CALL];library.persistent_test_run.restype=None

def main():
    rows=[]
    for action,initial in ((0,'stock'),(0,'candidate'),(1,'stock'),(2,'candidate'),(2,'stock'),(3,'stock'),(3,'candidate')):
        os=OS(action,initial);r=os.run();assert r['status']==0 and os.ro
        if action==1:assert os.equals('candidate') and [p for p,_,_ in os.program_writes][:8]==[CP]*8
        if action==2:assert os.equals('stock')
        if action==3:assert os.image_mode==0 and not os.program_writes
        rows.append(dict(case=f'normal-{action}-{initial}',passed=True,writes=r['writes']))
    for n in range(1,37):
        os=OS(1,fail_write=n);r=os.run();assert r['status'] and r['rollback']==0 and os.equals('stock') and os.ro
        rows.append(dict(case='install-write-failure',window=n,rollback_verified=True))
    for n in (1,8,9,36):
        os=OS(2,'candidate',fail_write=n);r=os.run();assert r['status'] and not r['rollback'] and os.equals('stock')
        rows.append(dict(case='undo-write-failure',window=n,stock_recovered=True))
    for fault in ({'short_write':True,'short_read':True,'report_short':True},{'eintr':True}):
        os=OS(1,**fault);r=os.run();assert r['status']==0 and os.equals('candidate');rows.append(dict(case='short-and-interrupted-transfers',fault=fault,passed=True))
    for fault in ({'sync_fail':1},{'sync_fail':2},{'readback_corrupt':True}):
        os=OS(1,**fault);r=os.run();assert r['status'] and not r['rollback'] and os.equals('stock');rows.append(dict(case='flush-or-readback-failure',fault=fault,stock_recovered=True))
    for fault in ({'mode':1},{'cache':1},{'model':15},{'not_root':True},{'owned_corrupt':True},{'size_bad':True},{'rw_fail':True},{'inode_changed':True},{'unlink_fail':True},{'dir_sync_fail':True},{'wrong_backend':True},{'close_n':1},{'shared_map':True},{'unrelocated':True},{'program_symlink':True}):
        os=OS(1,**fault);r=os.run();assert r['status'] and not os.program_writes;rows.append(dict(case='before-write-refusal',fault=fault,no_program_write=True))
    os=OS(2,mixed=True);r=os.run();assert r['status']==0 and os.equals('stock');rows.append(dict(case='known-mixed-undo',passed=True))
    os=OS(2,'candidate',initial_rw=True);r=os.run();assert not r['status'] and os.equals('stock') and os.ro;rows.append(dict(case='undo-recovers-known-rw-mount',passed=True))
    os=OS(1,fail_write=4,sticky_write=True);r=os.run();assert r['status'] and r['rollback'] and not os.equals('stock');rows.append(dict(case='rollback-itself-fails',reported=True))
    os=OS(1,ro_fail=True);r=os.run();assert r['status'] and r['readonly'] and os.equals('candidate') and not os.ro;rows.append(dict(case='readonly-restore-failure',reported=True))
    os=OS(1,close_n=3);r=os.run();assert r['status'] and os.equals('candidate');rows.append(dict(case='close-error-after-write',reported=True))
    for fault in ({'drop_write_fail':True},{'drop_close_fail':True},{'mode_write_fail':True}):
        os=OS(3,'candidate',**fault);r=os.run();assert r['status'] and not os.program_writes
        if fault.get('drop_write_fail'):assert os.image_mode==2
        if fault.get('drop_close_fail'):assert os.image_mode==0
        rows.append(dict(case='snapshot-error',fault=fault,reported=True))
    os=OS(0,outside_corrupt=True);r=os.run();assert r['status']==0 and not os.equals('stock')
    rows.append(dict(case='native-window-check-does-not-replace-whole-file-check',native_accepts=True,complete_host_readback_required=True))
    os=OS(0);r=os.run();assert r['cleanup_calls']['directory_open']>=0 and r['cleanup_calls']['directory_sync']==0 and os.report_nofollow
    rows.append(dict(case='target-UAPI-directory-and-no-follow-flags',flags=ABI,passed=True))
    report=dict(status='passed-offline',camera_io=False,cases=rows,count=len(rows),build_sha256=sha256(BUILD/'build.json'),
        test_sha256=sha256(ROOT/'tests/test_persistent_writer_native.py'),source_sha256=sha256(ROOT/'native/persistent_writer.c'),
        target_ABI_sources=ABI_SOURCES,
        limits=['Compiled C logic with target-UAPI-derived simulated syscalls and reduced-size manifests. Not physical filesystem, flash power-loss or USB testing.','Power loss cannot execute rollback; no hardware recovery guarantee is implied.'])
    (TEST_OUT/'native-tests.json').write_text(json.dumps(report,indent=2)+'\n');print('Passed native writer cases:',len(rows))

if __name__=='__main__':main()
