import json
from acquire import ROOT,sha256
from a7c2_readonly_backup import parse_snapshot,identity_digest
def expected_body():
 p=ROOT/"data/private/device"
 s=json.loads((p/"profile.json").read_text())
 assert sha256(p/"identity-baseline.bin")==s["baseline_sha256"]
 value=identity_digest(parse_snapshot((p/"identity-baseline.bin").read_bytes()))
 assert value==s["body_digest"]
 return value
