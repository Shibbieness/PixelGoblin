"""Dependency-free PNG read/write.

Writes 8-bit RGBA or indexed (palette + tRNS). Reads non-interlaced 8-bit
PNG of colour types 0, 2, 3, 4 and 6 — which covers what pixel artists and
most exporters produce. Anything else falls back to Pillow if it happens to
be installed, and otherwise fails with a plain-language message.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def encode_rgba(w: int, h: int, rgba: bytes) -> bytes:
    if len(rgba) != w * h * 4:
        raise ValueError("rgba length does not match size")
    raw = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")


def encode_indexed(w: int, h: int, indices: bytes, palette: list[tuple[int, int, int, int]]) -> bytes:
    """Indexed PNG: exact palette survives the round trip (important for
    engines that palette-swap)."""
    if len(palette) > 256:
        raise ValueError("indexed PNG holds at most 256 colours")
    raw = b"".join(b"\x00" + indices[y * w:(y + 1) * w] for y in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0)
    plte = b"".join(bytes(c[:3]) for c in palette)
    trns = bytes(c[3] for c in palette)
    return (SIG + _chunk(b"IHDR", ihdr) + _chunk(b"PLTE", plte) + _chunk(b"tRNS", trns)
            + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b""))


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode(data: bytes) -> tuple[int, int, bytes]:
    """Return (w, h, rgba bytes)."""
    if data[:8] != SIG:
        raise ValueError("not a PNG file")
    pos, idat, plte, trns = 8, [], b"", b""
    w = h = depth = ctype = interlace = None
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            plte = body
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if depth != 8 or interlace != 0 or ctype not in (0, 2, 3, 4, 6):
        raise ValueError(f"PNG variant not supported by the built-in reader (depth={depth}, colour type={ctype}, interlace={interlace}); install Pillow or re-save as 8-bit non-interlaced")
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(b"".join(idat))
    stride = w * bpp
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    for _ in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                line[x] = (line[x] + _paeth(a, b, c)) & 255
        out += line
        prev = line
    rgba = bytearray()
    for p in range(w * h):
        if ctype == 6:
            rgba += out[p * 4:p * 4 + 4]
        elif ctype == 2:
            rgba += out[p * 3:p * 3 + 3] + b"\xff"
        elif ctype == 0:
            g = out[p]
            rgba += bytes((g, g, g, 255))
        elif ctype == 4:
            g, a = out[p * 2], out[p * 2 + 1]
            rgba += bytes((g, g, g, a))
        else:
            k = out[p]
            r, g, b = plte[k * 3:k * 3 + 3]
            a = trns[k] if k < len(trns) else 255
            rgba += bytes((r, g, b, a))
    return w, h, bytes(rgba)


def read(path: str | Path) -> tuple[int, int, bytes]:
    data = Path(path).read_bytes()
    try:
        return decode(data)
    except ValueError:
        try:  # optional convenience, never required
            from PIL import Image  # type: ignore
        except ImportError:
            raise
        im = Image.open(path).convert("RGBA")
        return im.width, im.height, im.tobytes()
