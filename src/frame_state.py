"""Measured native BEBF screen-title signatures, including dimmed frames.

Only a small title region is classified. A final score is never inferred from
an intermediate score or elapsed time. Signatures store hashes, not ROM assets.
"""
import hashlib
import struct

TITLE_RECT=(52,4,204,30)
TITLE_HASHES={
    'bdebabbd5e0d10a1116c2eb40a01ce154e61c980cbb00a7f2816e140538d72fe':'result',
    '12a41f77c4091ce8db61d9bb492fc8eabe3ab845a8fec5454b11a9149e5b3abb':'halftime',
}


def green_region(frame, rectangle=TITLE_RECT):
    if frame is None:return b''
    width,height,data,pitch,format_id=frame
    left,top,right,bottom=rectangle
    if width!=256 or height!=384 or not 0<=left<right<=width or not 0<=top<bottom<=height:
        return b''
    values=bytearray()
    for y in range(top,bottom):
        if format_id==1:
            values.extend(data[y*pitch+left*4+1:y*pitch+right*4:4])
        elif format_id in (0,2):
            raw=struct.unpack_from('<'+'H'*(right-left),data,y*pitch+left*2)
            maximum=63 if format_id==2 else 31
            values.extend(((pixel>>5)&maximum)*255//maximum for pixel in raw)
        else:return b''
    return bytes(values)


def title_signature(values):
    if not values or max(values)-min(values)<8:return None
    threshold=min(values)+(max(values)-min(values))*2//3
    return hashlib.sha256(bytes(value>threshold for value in values)).hexdigest()


def screen_phase(frame):
    return TITLE_HASHES.get(title_signature(green_region(frame)))
