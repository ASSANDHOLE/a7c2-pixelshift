from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha256(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
 return h.hexdigest()
