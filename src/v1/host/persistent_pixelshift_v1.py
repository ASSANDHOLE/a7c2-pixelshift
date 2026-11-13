import hashlib
from acquire import ROOT
OUT=ROOT/"data/private/device"
def digest(data):return hashlib.sha256(data).hexdigest()
