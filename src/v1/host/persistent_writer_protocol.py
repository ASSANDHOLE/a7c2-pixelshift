"""Closed USB vocabulary and nonce-bound reports for the persistent writer."""
import hashlib,json,struct,uuid
from a7c2_readonly_protocol import Protocol,OutgoingPolicy,HEADER,SEGMENT,CHUNK,SERVICE_PID,PolicyError,ProtocolError
from a7c2_readonly_backup import MAX_SNAPSHOT

STAGING='/tmp/jiritsu/libJit.so'
REQUEST='/tmp/jiritsu/a7c2.persistent.request'
RESULT='/tmp/jiritsu/a7c2.persistent.result'
PROGRAMS={'AP':'/tmp/jiritsu/../../usr/lib/appFw.so','CP':'/tmp/jiritsu/../../cp/cpapp-b.bin'}
PATHS=(STAGING,REQUEST,RESULT,*PROGRAMS.values())
Q=struct.Struct('<8sII16s');R=struct.Struct('<8sII16s4q2Q12I128s40s3q2I');R2=struct.Struct(R.format+'5q')

def request(action):
    if action not in range(4):raise ValueError('Unknown fixed action')
    return Q.pack(b'A7PWQ001',1,action,uuid.uuid4().bytes)

def request_fields(raw):
    if len(raw)!=Q.size:raise ValueError('Request length')
    magic,version,action,nonce=Q.unpack(raw)
    if magic!=b'A7PWQ001' or version!=1 or action not in range(4) or not any(nonce):raise ValueError('Request shape')
    return action,nonce

def parse(raw,expected):
    action,nonce=request_fields(expected)
    if len(raw)<16:raise ValueError('Incomplete native report')
    version=struct.unpack_from('<I',raw,8)[0];layout=R if version==1 else R2 if version==2 else None
    if layout is None or len(raw)!=layout.size+24:raise ValueError('Incomplete native report')
    v=layout.unpack(raw[:layout.size])
    if v[:4]!=(b'A7PWR001',version,action,nonce) or raw[layout.size:]!=b'A7PWEND1'+nonce:raise ValueError('Report nonce/version/footer')
    keys=('status','rollback','readonly','cleanup','pid','base','phase','writes','writebytes','model','mode','cache','loaded','mutated')
    result=dict(zip(keys,v[4:18]));result.update(report_version=version,action=action,nonce=nonce.hex(),before_state=list(v[18:20]),after_state=list(v[20:22]),
        before_window_sha256=[v[22][i:i+32].hex() for i in (0,32)],after_window_sha256=[v[22][i:i+32].hex() for i in (64,96)],
        boot_id=v[23].split(b'\0',1)[0].decode('ascii').strip(),drop_result=v[24],mode_result=v[25],log_result=v[26],flags=v[27],image_mode=v[28],snapshot_backend_valid=bool(v[27]&8))
    if result['phase']>7 or result['writes']>6 or result['writebytes']>24:raise ValueError('Report bounds')
    if version==2:result['cleanup_calls']=dict(zip(('unlink_helper','unlink_request','directory_open','directory_sync','directory_close'),v[29:34]))
    if result['status']==0:
        if not result['flags']&1 or result['model']!=16 or result['mode'] or result['cache'] or result['readonly'] or result['cleanup']:raise ValueError('Success contract differs')
        uuid.UUID(result['boot_id'])
    return result

class Policy(OutgoingPolicy):
    def __init__(self,pid,helper,actions):
        super().__init__(pid);self.helper=helper;self.actions=set(actions);self.selected=None;self.request=None;self.uploaded=set();self.used=set();self.cleanup=set();self.backups=0;self.calls=0
    def arm(self,raw):
        action,nonce=request_fields(raw)
        if action not in self.actions or nonce in self.used or self.calls>=4:raise PolicyError('Action/replay/quota')
        self.used.add(nonce);self.request=raw;self.uploaded=set();self.calls+=1
    def bulk(self,data):
        if self.state=='auth':return super().bulk(data)
        if self.state!='ready' or self.pid!=SERVICE_PID or self.sequence>192 or len(data)<16:raise PolicyError('Session/quota')
        if HEADER.unpack_from(data)!=(len(data)-12,0x40,self.sequence,0,0,0,0):raise PolicyError('Framing')
        g,c=struct.unpack_from('<HH',data,12);p=data[16:]
        if (g,c)==(0x603,5) and p in (b'\0',b'\1'):
            if self.backups>=4:raise PolicyError('Backup quota')
            self.backups+=1
        elif g==0x1001:
            if c==15:
                allowed={b'\0'+s.encode()+b'\0':s for s in PATHS}
                if p not in allowed:raise PolicyError('Unapproved path')
                self.selected=allowed[p]
            elif c==17:
                if self.selected not in PATHS or p!=b'\0\xff\0':raise PolicyError('Read shape')
            elif c==16:
                if self.request is None or self.selected not in (STAGING,REQUEST) or self.selected in self.uploaded:raise PolicyError('Unarmed/repeated upload')
                content=self.helper if self.selected==STAGING else self.request
                if p!=b'\0\xff\0'+content or self.selected==STAGING and REQUEST not in self.uploaded:raise PolicyError('Unreviewed upload/order')
                self.uploaded.add(self.selected)
            elif c==18:
                if self.selected not in self.cleanup or self.selected in PROGRAMS.values() or p!=b'\0\xff':raise PolicyError('Unowned cleanup')
                self.cleanup.remove(self.selected)
            else:raise PolicyError('Unapproved file operation')
        else:raise PolicyError('Unapproved USB command')
        self.sequence+=1

class WriterProtocol(Protocol):
    def __init__(self,raw,pid,keys,helper,actions,sizes,event=lambda *a,**k:None):
        super().__init__(raw,pid,keys,event);self.policy=Policy(pid,helper,actions);self.sizes=sizes
    def exchange(self,group,command,payload,max_size):
        seq=self.policy.sequence;data=struct.pack('<HH',group,command)+payload;self.raw.begin(180)
        try:
            self._write(HEADER.pack(len(data),0x40,seq,0,0,0,0)+data);out=bytearray();remaining=None
            while True:
                n,f,s,_,_,_,status=HEADER.unpack(self._read(HEADER.size))
                if f!=0x40 or s!=seq or status or not 0<n<=max_size or remaining is not None and n!=remaining:raise ProtocolError('Reply framing/size')
                take=min(n,SEGMENT)
                for offset in range(0,take,CHUNK):out.extend(self._read(min(CHUNK,take-offset)))
                if len(out)>max_size:raise ProtocolError('Response cap')
                if n<=SEGMENT:break
                remaining=n-SEGMENT
            return bytes(out)
        except BaseException:self.healthy=False;self.policy.poison();raise
    def jiritsu(self,command,payload,missing=False):
        cap=65540
        if command==17:
            for name,path in PROGRAMS.items():
                if self.policy.selected==path:cap=self.sizes[name]+4
        raw=self.exchange(0x1001,command,payload,cap)
        if len(raw)<4:raise ProtocolError('Short file reply')
        status=struct.unpack_from('<I',raw)[0]
        if missing and status==0x10000006 and len(raw)==4:return None
        if status:raise ProtocolError(f'File response {status:#x}')
        return raw[4:]
    def select(self,path):
        if path not in PATHS:raise PolicyError('Unapproved path')
        self.jiritsu(15,b'\0'+path.encode()+b'\0')
    def read_file(self,path):self.select(path);return self.jiritsu(17,b'\0\xff\0',True)
    def upload(self,path,data):self.select(path);return self.jiritsu(16,b'\0\xff\0'+data)
    def snapshot(self,memory):return self.exchange(0x603,5,bytes([int(memory)]),MAX_SNAPSHOT)
    def delete_verified(self,path,expected):
        if path not in (STAGING,REQUEST,RESULT) or self.read_file(path)!=expected:raise PolicyError('Cleanup identity')
        self.policy.cleanup.add(path);self.select(path);self.jiritsu(18,b'\0\xff')
        if self.read_file(path) is not None:raise PolicyError('Cleanup not confirmed')
