"""Share codes — a whole sprite in a short string.

Layout (19 bytes): engine_major (1) | type_hash prefix (8) | seed (8) |
checksum (2). Base32 (Crockford alphabet, no padding), grouped for reading
aloud. The type file itself is not in the code; the receiver must hold the
same type file, which is exactly the determinism contract.
"""

from __future__ import annotations

from . import ENGINE_MAJOR
from .rng import sha256

ALPHA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _b32(b: bytes) -> str:
    n, bits, out = 0, 0, []
    for byte in b:
        n = (n << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            out.append(ALPHA[(n >> bits) & 31])
    if bits:
        out.append(ALPHA[(n << (5 - bits)) & 31])
    return "".join(out)


def _unb32(s: str) -> bytes:
    n, bits, out = 0, 0, bytearray()
    for ch in s:
        ch = {"O": "0", "I": "1", "L": "1"}.get(ch, ch)
        if ch not in ALPHA:
            raise ValueError(f"share code contains {ch!r}, which is not a share-code character")
        n = (n << 5) | ALPHA.index(ch)
        bits += 5
        if bits >= 8:
            bits -= 8
            out.append((n >> bits) & 255)
    return bytes(out)


def encode(type_hash: str, seed: int) -> str:
    body = bytes([ENGINE_MAJOR]) + bytes.fromhex(type_hash)[:8] + seed.to_bytes(8, "little")
    raw = body + sha256(body)[:2]
    s = _b32(raw)
    return "PG-" + "-".join(s[i:i + 5] for i in range(0, len(s), 5))


def decode(code: str) -> dict:
    s = code.upper().replace("PG-", "", 1).replace("-", "").replace(" ", "")
    raw = _unb32(s)[:19]
    if len(raw) != 19:
        raise ValueError("share code is the wrong length — check for a missing group")
    body, chk = raw[:17], raw[17:]
    if sha256(body)[:2] != chk:
        raise ValueError("share code checksum does not match — a character was mistyped")
    return {"engine_major": body[0], "type_hash_prefix": body[1:9].hex(), "seed": int.from_bytes(body[9:17], "little")}
