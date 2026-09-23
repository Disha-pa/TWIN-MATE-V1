import struct
import zlib
import os

os.makedirs("static/icons", exist_ok=True)


def write_png(path, size, rgb=(181, 216, 255)):
    w, h = size, size
    r, g, b = rgb
    row = bytes([0] + [r, g, b] * w)
    raw = row * h
    compressed = zlib.compress(raw, 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(
            ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
        )

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


write_png("static/icons/icon-192.png", 192)
write_png("static/icons/icon-512.png", 512)
print("icons created")
