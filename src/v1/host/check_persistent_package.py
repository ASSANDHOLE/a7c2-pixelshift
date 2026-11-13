from persistent_pixelshift_v1 import digest

def identify(data,row):
    if len(data)!=row['bytes']:raise ValueError('File length differs')
    actual=digest(data)
    if actual==row['stock_sha256']:
        return 'unchanged' if row['stock_sha256']==row['candidate_sha256'] else 'stock'
    if actual==row['candidate_sha256']:return 'candidate'
    original=bytearray(data)
    for span in row['spans']:
        at=span['offset'];before=bytes.fromhex(span['before_hex']);after=bytes.fromhex(span['after_hex']);part=data[at:at+len(before)]
        if any(v not in (a,b) for v,a,b in zip(part,before,after)):raise ValueError('Unknown bytes inside an owned window')
        original[at:at+len(before)]=before
    if digest(original)!=row['stock_sha256']:raise ValueError('Unowned bytes differ')
    return 'known-mixed-not-boot-certified'

def restore_local_bytes(data,row):
    identify(data,row);restored=bytearray(data)
    for span in row['spans']:
        at=span['offset'];before=bytes.fromhex(span['before_hex']);restored[at:at+len(before)]=before
    assert digest(restored)==row['stock_sha256']
    return bytes(restored)

