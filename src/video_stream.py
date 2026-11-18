"""JPEG frames for the continuous, bounded-latency MJPEG arena stream."""
from io import BytesIO
from PIL import Image


def encode_jpeg(frame):
    width, height, pixels, pitch, pixel_format = frame
    if pixel_format == 1:
        image = Image.frombytes('RGB', (width, height), pixels, 'raw', 'BGRX', pitch)
    else:
        import struct
        rgb = bytearray()
        for y in range(height):
            values = struct.unpack_from('<'+'H'*width, pixels, y*pitch)
            if pixel_format == 2:
                rgb.extend(c for v in values for c in (((v>>11)&31)*255//31, ((v>>5)&63)*255//63, (v&31)*255//31))
            else:
                rgb.extend(c for v in values for c in (((v>>10)&31)*255//31, ((v>>5)&31)*255//31, (v&31)*255//31))
        image = Image.frombytes('RGB', (width, height), bytes(rgb))
    output = BytesIO()
    image.save(output, format='JPEG', quality=85, subsampling=0)
    return output.getvalue()
