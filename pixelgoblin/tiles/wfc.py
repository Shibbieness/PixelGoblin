"""Wave Function Collapse, overlapping model (after mxgmn, MIT), integer-only.

Output is periodic, so every result tiles seamlessly — useful for floors,
walls, water and cave textures. WFC can reach a contradiction and return
nothing; PixelGoblin never returns nothing:

    seeded retry (up to `attempts`, each on its own stream)
      -> fallback: periodic tiling of the sample, clearly flagged

The fallback count is reported, never hidden, so a sample that contradicts
often is visible as a design problem rather than a silent quality drop.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..rng import Rng, derive
from ..sprite import Sprite

DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))


@dataclass
class WfcResult:
    sprite: Sprite
    attempts: int
    fallback: bool
    patterns: int


def _patterns(sample: Sprite, n: int):
    w, h = sample.w, sample.h
    order, counts = [], {}
    for y in range(h):
        for x in range(w):
            p = tuple(sample.px[((y + dy) % h) * w + (x + dx) % w] for dy in range(n) for dx in range(n))
            if p not in counts:
                counts[p] = 0
                order.append(p)
            counts[p] += 1
    return order, [counts[p] for p in order]


def _agrees(p, q, dx, dy, n) -> bool:
    for y in range(n):
        for x in range(n):
            x2, y2 = x - dx, y - dy
            if 0 <= x2 < n and 0 <= y2 < n and p[y * n + x] != q[y2 * n + x2]:
                return False
    return True


def generate(sample: Sprite, width: int, height: int, seed16: bytes, n: int = 3, attempts: int = 8) -> WfcResult:
    pats, weights = _patterns(sample, n)
    P = len(pats)
    full = (1 << P) - 1
    compat = [[0] * P for _ in DIRS]
    for d, (dx, dy) in enumerate(DIRS):
        for i in range(P):
            m = 0
            for j in range(P):
                if _agrees(pats[i], pats[j], dx, dy, n):
                    m |= 1 << j
            compat[d][i] = m
    for a in range(attempts):
        rng = Rng(derive(seed16, f"attempt/{a}"))
        wave = [full] * (width * height)
        ok = True
        while True:
            best, cands = None, []
            for c, m in enumerate(wave):
                k = m.bit_count()
                if k == 0:
                    ok = False
                    break
                if k > 1:
                    if best is None or k < best:
                        best, cands = k, [c]
                    elif k == best:
                        cands.append(c)
            if not ok or best is None:
                break
            c = cands[rng.below(len(cands))]
            opts = [j for j in range(P) if wave[c] >> j & 1]
            pick = opts[rng.weighted([weights[j] for j in opts])]
            wave[c] = 1 << pick
            stack = [c]
            while stack and ok:
                cur = stack.pop()
                cx, cy = cur % width, cur // width
                for d, (dx, dy) in enumerate(DIRS):
                    nb = ((cy + dy) % height) * width + (cx + dx) % width
                    allowed = 0
                    m = wave[cur]
                    j = 0
                    while m:
                        if m & 1:
                            allowed |= compat[d][j]
                        m >>= 1
                        j += 1
                    new = wave[nb] & allowed
                    if new != wave[nb]:
                        if new == 0:
                            ok = False
                            break
                        wave[nb] = new
                        stack.append(nb)
        if ok:
            out = Sprite(width, height, list(sample.palette))
            for c, m in enumerate(wave):
                out.px[c] = pats[m.bit_length() - 1][0]
            return WfcResult(out, a + 1, False, P)
    out = Sprite(width, height, list(sample.palette))
    for y in range(height):
        for x in range(width):
            out.px[y * width + x] = sample.px[(y % sample.h) * sample.w + x % sample.w]
    return WfcResult(out, attempts, True, P)


def sample_from_rows(rows: list[str], colors: dict[str, tuple]) -> Sprite:
    s = Sprite(len(rows[0]), len(rows))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            s.px[y * s.w + x] = s.color_index(colors[ch])
    return s
