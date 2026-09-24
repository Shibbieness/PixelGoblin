"""Parallax background generator — skies, mountain ranges, hills, reef shelves.

Integer value noise (lowbias32 lattice + integer smoothstep) per layer,
ordered Bayer 4x4 dithering between colour bands (stable in motion, unlike
error diffusion). Each layer also exports on its own with a scroll factor so
engines can build real parallax.
"""

from __future__ import annotations

from .. import ENGINE_MAJOR
from ..rng import M32, Streams, hash32, master_seed
from ..sprite import TRANSPARENT, Sprite, hex_to_rgba

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def _lattice(seed: int, octave: int, i: int, amp: int) -> int:
    if amp == 0:
        return 0
    h = hash32(seed ^ ((i * 0x9E3779B1) & M32) ^ ((octave * 0x632BE5AB) & M32))
    return h % (2 * amp + 1) - amp


def noise1d(seed: int, x: int, periods: list[int], amps: list[int]) -> int:
    total = 0
    for o in range(len(periods)):
        p, a = periods[o], amps[o]
        i, t = x // p, x % p
        va, vb = _lattice(seed, o, i, a), _lattice(seed, o, i + 1, a)
        s = (t * t * (3 * p - 2 * t) * 1024) // (p * p * p)
        total += (va * 1024 + (vb - va) * s) // 1024
    return total


def _band(depth: int, span: int, n: int, x: int, y: int) -> int:
    band = depth * (n - 1) * 16 // max(1, span)
    b, f = band // 16, band % 16
    return b + 1 if f > BAYER4[y % 4][x % 4] and b + 1 <= n - 1 else b


def generate(tf, seed: int, overrides=None) -> Sprite:
    return generate_frames(tf, seed, overrides)[0]


def generate_frames(tf, seed: int, overrides=None) -> list[Sprite]:
    return [generate_layers(tf, seed, overrides)[0][2]]


def generate_layers(tf, seed: int, overrides=None):
    """Returns [("composite", 0, sprite), (layer name, scroll %, sprite), ...]."""
    data = tf.data
    S = Streams(master_seed(tf.type_hash, seed, ENGINE_MAJOR), overrides)
    W, H = data["size"]
    sky = [hex_to_rgba(c) for c in data["palette"]["sky"]]
    star = hex_to_rgba(data["palette"].get("star", "#f4f4f4"))
    pal = [TRANSPARENT, star] + sky
    offs = []
    for L in data["layers"]:
        offs.append(len(pal))
        pal += [hex_to_rgba(c) for c in L["colors"]]
    comp = Sprite(W, H, pal)
    n = len(sky)
    for y in range(H):
        for x in range(W):
            comp.px[y * W + x] = 2 + _band(y, H - 1, n, x, y)
    rng = S.rng("stars")
    for _ in range(data.get("stars", 0)):
        x, y = rng.below(W), rng.below(max(1, H * 2 // 5))
        comp.px[y * W + x] = 1
    out = [("composite", 0, comp)]
    for li, L in enumerate(data["layers"]):
        lseed = S.rng("layer/" + L["name"]).next()
        layer = Sprite(W, H, pal)
        base_y = H * L["base"] // 100
        cols = len(L["colors"])
        for x in range(W):
            top = base_y - noise1d(lseed, x, L["periods"], L["amps"])
            for y in range(max(0, top), H):
                depth = y - top
                ci = cols - 1 if depth == 0 else (cols - 1) - _band(depth, H - top, cols, x, y)
                idx = offs[li] + ci
                layer.px[y * W + x] = idx
                comp.px[y * W + x] = idx
        out.append((L["name"], L["scroll"], layer))
    return out
