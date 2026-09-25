"""Seeded, integer-only randomness.

xoshiro128** (32-bit operations only) so that Python, JavaScript (Math.imul)
and the future Rust core produce bit-identical streams. Seeds are derived
with SHA-256 so every named part of a sprite owns an independent stream:
adding a new part never reshuffles an existing one (ADR-008).
"""

from __future__ import annotations

import hashlib

M32 = 0xFFFFFFFF


def _rotl(x: int, k: int) -> int:
    return ((x << k) | (x >> (32 - k))) & M32


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def derive(seed16: bytes, path: str) -> bytes:
    """Child seed for a named stream. Order-independent by construction."""
    if len(seed16) != 16:
        raise ValueError("seed must be 16 bytes")
    return sha256(seed16 + b"/" + path.encode("utf-8"))[:16]


def master_seed(type_hash_hex: str, user_seed: int, engine_major: int) -> bytes:
    if not 0 <= user_seed < 2 ** 64:
        raise ValueError("seed must be an integer in 0 .. 2^64-1")
    data = b"PG" + bytes.fromhex(type_hash_hex) + user_seed.to_bytes(8, "little") + bytes([engine_major & 0xFF])
    return sha256(data)[:16]


def hash32(x: int) -> int:
    """lowbias32 integer hash — used for position-keyed noise."""
    x &= M32
    x ^= x >> 16
    x = (x * 0x7FEB352D) & M32
    x ^= x >> 15
    x = (x * 0x846CA68B) & M32
    x ^= x >> 16
    return x


class Rng:
    __slots__ = ("s0", "s1", "s2", "s3")

    def __init__(self, seed16: bytes):
        if len(seed16) != 16:
            raise ValueError("seed must be 16 bytes")
        s = [int.from_bytes(seed16[i:i + 4], "little") for i in range(0, 16, 4)]
        if not any(s):
            s[0] = 1
        self.s0, self.s1, self.s2, self.s3 = s

    def next(self) -> int:
        s0, s1, s2, s3 = self.s0, self.s1, self.s2, self.s3
        result = (_rotl((s1 * 5) & M32, 7) * 9) & M32
        t = (s1 << 9) & M32
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = _rotl(s3, 11)
        self.s0, self.s1, self.s2, self.s3 = s0, s1, s2, s3
        return result

    def below(self, n: int) -> int:
        """Unbiased integer in [0, n)."""
        if n <= 0:
            raise ValueError("below(n) needs n > 0")
        limit = (0x100000000 // n) * n
        while True:
            r = self.next()
            if r < limit:
                return r % n

    def range(self, lo: int, hi: int) -> int:
        """Inclusive integer range."""
        return lo + self.below(hi - lo + 1)

    def chance(self, percent: int) -> bool:
        return self.below(100) < percent

    def weighted(self, weights: list[int]) -> int:
        total = sum(weights)
        if total <= 0:
            raise ValueError("weights must sum to > 0")
        r = self.below(total)
        for i, w in enumerate(weights):
            if r < w:
                return i
            r -= w
        raise AssertionError("unreachable")


class Streams:
    """Named streams under one master seed.

    `overrides` lets brood (seed genealogy) hand a part the stream of a
    parent, without the generator knowing anything about parents.
    """

    def __init__(self, master16: bytes, overrides: dict[str, bytes] | None = None):
        self.master = master16
        self.overrides = overrides or {}

    def seed(self, path: str) -> bytes:
        if path in self.overrides:
            return self.overrides[path]
        return derive(self.master, path)

    def rng(self, path: str) -> Rng:
        return Rng(self.seed(path))


def seed_from_name(name: str) -> int:
    """A name is a seed: 'Grubnak' always makes the same goblin. Case and
    surrounding spaces do not matter; the rest of the name does."""
    return int.from_bytes(sha256(("name:" + " ".join(name.split()).lower()).encode("utf-8"))[:8], "little")
