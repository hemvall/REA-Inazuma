"""Bounded BEBF patch: enable the two isolated club encounters in course 1."""
import struct
import sys
from pathlib import Path
from nds import sha, Rom


def unlock_route(data):
    # ndspy is used only to decode/recompress the original ARM9 overlay.
    try:
        from ndspy import codeCompression
    except ImportError:
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local/python-deps'))
        from ndspy import codeCompression
    result=bytearray(data)
    table,table_size=struct.unpack_from('<II',data,0x50)
    entries=[table+i for i in range(0,table_size,32)]
    entry=next(at for at in entries if struct.unpack_from('<I',data,at)[0]==15)
    _,base,ram_size,_,_,_,file_id,flags=struct.unpack_from('<8I',data,entry)
    if base!=0x02131A40 or ram_size!=227200:
        raise ValueError('Unsupported native route overlay')
    fat=struct.unpack_from('<I',data,0x48)[0]
    start,end=struct.unpack_from('<II',data,fat+file_id*8)
    original=bytes(data[start:end])
    decoded=bytearray(codeCompression.decompress(original))
    if sha(decoded)!='419a3c6bb88bb3d1aad3a09f339b5b1324a3b886938a2766823c64a8b4159ed3':
        raise ValueError('Native route overlay identity changed')
    at=0x02163A58-base
    # Keep argument decoding and script completion intact. Set only course 1's
    # enabled byte and root/two-node visibility/selectability bitmaps. Match
    # grades and victory counts remain untouched.
    words=(0xE59F0044,0xE3A01001,0xE5C01042,
           0xE5902044,0xE3822007,0xE5802044,
           0xE590204C,0xE3822007,0xE580204C)
    decoded[at:at+36]=struct.pack('<9I',*words)
    struct.pack_into('<I',decoded,0x02163AA4-base,0x020CADE0)
    packed=codeCompression.compress(decoded,False)
    if len(packed)>end-start:
        raise ValueError('Native overlay exceeds its original allocation')
    result[start:end]=packed+bytes(end-start-len(packed))
    struct.pack_into('<I',result,fat+file_id*8+4,start+len(packed))
    struct.pack_into('<I',result,entry+28,(flags&0xFF000000)|len(packed))
    if codeCompression.decompress(packed)!=decoded:
        raise ValueError('Native overlay compression roundtrip failed')
    Rom(result)
    restored=bytearray(result)
    restored[start:end]=original
    restored[fat+file_id*8:fat+file_id*8+8]=data[fat+file_id*8:fat+file_id*8+8]
    restored[entry:entry+32]=data[entry:entry+32]
    if restored!=data:
        raise ValueError('Native overlay reverse validation failed')
    return bytes(result),{'overlay':15,'before_sha256':sha(original),
        'after_sha256':sha(packed),'changed_code_bytes':40,'course':1,'matches':2,
        'reverse_verified':True}
