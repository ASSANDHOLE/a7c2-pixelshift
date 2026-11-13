import re
from acquire import ROOT
BUILD=ROOT/"data/private/device/writer"
def target_flags():
    # Reuse the independently UAPI-derived model introduced after the earlier
    # four-frame cleanup failure. Never take Windows/x86 os.O_* constants.
    from abi_reference import abi
    flags,sources=abi();generic=(ROOT/'sdk/headers/any-linux-any/asm-generic/fcntl.h').read_text()
    for name in ('O_RDWR','O_NONBLOCK','O_TRUNC','O_APPEND'):
        m=re.search(r'^#\s*define\s+'+name+r'\s+([0-7]+)\s',generic,re.M);assert m,name;flags[name]=int(m.group(1),8)
    flags['AT_FDCWD']=-100
    return flags,sources
