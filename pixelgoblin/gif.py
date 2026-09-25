"""Animated GIF export, stdlib only (GIF89a, LZW, looping, transparency).

Index 0 stays transparent. Frames must share a palette (every generator's
frames do); `write` merges palettes by exact colour if they differ.
"""

from __future__ import annotations

import struct
from pathlib import Path

from .sprite import Sprite


def _lzw(indices: bytes, min_size: int) -> bytes:
    clear, end = 1 << min_size, (1 << min_size) + 1
    size = min_size + 1
    table = {bytes([i]): i for i in range(clear)}
    nxt = end + 1
    out, acc, nbits = bytearray(), 0, 0

    def emit(code):
        nonlocal acc, nbits
        acc |= code << nbits
        nbits += size
        while nbits >= 8:
            out.append(acc & 255)
            acc >>= 8
            nbits -= 8

    emit(clear)
    w = b""
    for b in indices:
        wc = w + bytes([b])
        if wc in table:
            w = wc
            continue
        emit(table[w])
        if nxt < 4096:
            table[wc] = nxt
            nxt += 1
            if nxt > (1 << size) and size < 12:
                size += 1
        else:
            emit(clear)
            table = {bytes([i]): i for i in range(clear)}
            nxt, size = end + 1, min_size + 1
        w = bytes([b])
    if w:
        emit(table[w])
    emit(end)
    if nbits:
        out.append(acc & 255)
    blocks = bytearray()
    for i in range(0, len(out), 255):
        chunk = out[i:i + 255]
        blocks.append(len(chunk))
        blocks += chunk
    return bytes(blocks) + b"\x00"


def encode(frames: list[Sprite], frame_ms: int, scale: int = 1, loop: bool = True) -> bytes:
    pal: list = []
    maps = []
    for f in frames:
        m = []
        for c in f.palette:
            key = (0, 0, 0, 0) if c[3] == 0 else c
            if key not in pal:
                pal.append(key)
            m.append(pal.index(key))
        maps.append(m)
    if (0, 0, 0, 0) in pal:  # transparent first
        pal.remove((0, 0, 0, 0))
    pal.insert(0, (0, 0, 0, 0))
    maps = [[pal.index((0, 0, 0, 0) if f.palette[i][3] == 0 else f.palette[i]) for i in range(len(f.palette))] for f in frames]
    if len(pal) > 256:
        raise ValueError("GIF allows at most 256 colours across all frames")
    bits = max(1, (len(pal) - 1).bit_length())
    W, H = frames[0].w * scale, frames[0].h * scale
    out = bytearray(b"GIF89a" + struct.pack("<HHBBB", W, H, 0x80 | (bits - 1), 0, 0))
    for i in range(1 << bits):
        c = pal[i] if i < len(pal) else (0, 0, 0, 0)
        out += bytes(c[:3])
    if loop:
        out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
    delay = max(2, frame_ms // 10)
    for f, m in zip(frames, maps):
        s = f.scaled(scale) if scale > 1 else f
        out += b"\x21\xf9\x04" + bytes([0x09]) + struct.pack("<H", delay) + b"\x00\x00"
        out += b"\x2c" + struct.pack("<HHHHB", 0, 0, W, H, 0)
        idx = bytes(m[i] for i in s.px)
        out += bytes([max(2, bits)]) + _lzw(idx, max(2, bits))
    out += b"\x3b"
    return bytes(out)


def write(path, frames: list[Sprite], frame_ms: int, scale: int = 1) -> None:
    Path(path).write_bytes(encode(frames, frame_ms, scale))


def decode_frame_count(data: bytes) -> int:
    """Minimal reader used by the gates: counts image descriptors."""
    n = 0
    i = 13 + (3 << ((data[10] & 7) + 1) if data[10] & 0x80 else 0)
    while i < len(data):
        b = data[i]
        if b == 0x3B:
            break
        if b == 0x21:
            i += 2
            while data[i]:
                i += data[i] + 1
            i += 1
        elif b == 0x2C:
            n += 1
            flags = data[i + 9]
            i += 10 + ((3 << ((flags & 7) + 1)) if flags & 0x80 else 0)
            i += 1
            while data[i]:
                i += data[i] + 1
            i += 1
        else:
            raise ValueError("not a GIF block")
    return n
