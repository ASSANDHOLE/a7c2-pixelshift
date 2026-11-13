import json,re
from acquire import ROOT,sha256
PREFIX="sdk/headers/"
def abi():
    names=[PREFIX+'aarch64-linux-any/asm/fcntl.h',PREFIX+'any-linux-any/asm-generic/fcntl.h',
        PREFIX+'any-linux-any/linux/fcntl.h',PREFIX+'aarch64-linux-gnu/bits/fcntl.h']
    inventory={r['path']:r for r in json.loads((ROOT/'sdk/headers/inventory.json').read_text())}
    for name in names:assert sha256(ROOT/name)==inventory[name]['sha256']
    arch=(ROOT/names[0]).read_text();generic=(ROOT/names[1]).read_text()
    out={}
    for name in ('O_DIRECTORY','O_NOFOLLOW','O_DIRECT','O_LARGEFILE','O_RDONLY','O_WRONLY','O_CREAT','O_EXCL'):
        source=arch if name in ('O_DIRECTORY','O_NOFOLLOW','O_DIRECT','O_LARGEFILE') else generic
        match=re.search(r'^#\s*define\s+'+name+r'\s+([0-7]+)\s',source,re.M);assert match,name
        out[name]=int(match.group(1),8)
    assert out['O_DIRECTORY']==0x4000 and out['O_DIRECT']==0x10000 and out['O_NOFOLLOW']==0x8000
    libc=(ROOT/names[3]).read_text()
    for name in ('O_DIRECTORY','O_NOFOLLOW','O_DIRECT'):
        m=re.search(r'^#\s*define\s+__'+name+r'\s+([0-7]+)\s',libc,re.M);assert int(m.group(1),8)==out[name]
    return out,[dict(path=n,sha256=sha256(ROOT/n)) for n in names]
