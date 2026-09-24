"""L-system generator — trees, shrubs, fungi, coral, roots.

Symbols:  F draw forward   + turn left 45°   - turn right 45°
          [ push           ] leaf at the tip, then pop
          L leaf here      anything else: no drawing (used by rules)

Integer turtle on 8 directions, Bresenham lines, stochastic rules chosen
with integer weights. Streams: grow (rule choice), step (segment lengths),
fruit (fruit on leaves).
"""

from __future__ import annotations

from .. import ENGINE_MAJOR
from ..rng import Streams, master_seed
from ..sprite import TRANSPARENT, Sprite, hex_to_rgba

DIRS = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]  # E NE N NW W SW S SE


def expand(data: dict, S: Streams) -> str:
    rng = S.rng("grow")
    rules = data["rules"]
    s = data["axiom"]
    for _ in range(data["iterations"]):
        out = []
        for ch in s:
            if ch in rules:
                opts = rules[ch]
                out.append(opts[rng.weighted([o["weight"] for o in opts])]["to"] if len(opts) > 1 else opts[0]["to"])
            else:
                out.append(ch)
        s = "".join(out)
    return s


def line(x0, y0, x1, y1):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    pts = []
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def generate(tf, seed: int, overrides=None) -> Sprite:
    return generate_frames(tf, seed, overrides)[0]


def generate_frames(tf, seed: int, overrides=None) -> list[Sprite]:
    data = tf.data
    S = Streams(master_seed(tf.type_hash, seed, ENGINE_MAJOR), overrides)
    W, H = data["size"]
    prog = expand(data, S)
    step_rng, fruit_rng = S.rng("step"), S.rng("fruit")
    lo, hi = data["step"]
    rad = data["leaf_radius"]
    tw = data["trunk_width"]
    # cell kinds: 0 empty, 1 bark, 2 leaf, 3 fruit ; depth per bark cell for shading
    cells = [[0] * W for _ in range(H)]
    x, y, d, depth = W // 2, H - 2, 2, 0
    stack = []

    def put(px, py, kind):
        if 1 <= px < W - 1 and 1 <= py < H - 1:
            if kind == 1 or cells[py][px] == 0 or (kind == 3 and cells[py][px] == 2):
                cells[py][px] = kind

    def leaf(cx, cy):
        fruit = fruit_rng.chance(data["fruit_chance"])
        for oy in range(-rad, rad + 1):
            for ox in range(-rad, rad + 1):
                if abs(ox) + abs(oy) <= rad:
                    put(cx + ox, cy + oy, 2)
        if fruit:
            put(cx, cy + (1 if rad else 0), 3)

    for ch in prog:
        if ch == "F":
            n = step_rng.range(lo, hi)
            dx, dy = DIRS[d]
            nx, ny = x + dx * n, y + dy * n
            for px, py in line(x, y, nx, ny):
                put(px, py, 1)
                if depth == 0 and tw == 2:
                    put(px + 1, py, 1)
            x, y = nx, ny
        elif ch == "+":
            d = (d + 1) % 8
        elif ch == "-":
            d = (d + 7) % 8
        elif ch == "[":
            stack.append((x, y, d, depth))
            depth += 1
        elif ch == "]":
            leaf(x, y)
            if stack:
                x, y, d, depth = stack.pop()
        elif ch == "L":
            leaf(x, y)

    bark = [hex_to_rgba(c) for c in data["palette"]["bark"]]
    leafc = [hex_to_rgba(c) for c in data["palette"]["leaf"]]
    pal = [TRANSPARENT, hex_to_rgba(data["palette"]["outline"]), hex_to_rgba(data["palette"]["fruit"])] + bark + leafc
    ob, ol = 3, 3 + len(bark)
    spr = Sprite(W, H, pal)
    for yy in range(H):
        for xx in range(W):
            k = cells[yy][xx]
            if k == 0:
                touch = any(0 <= xx + a < W and 0 <= yy + b < H and cells[yy + b][xx + a]
                            for a, b in ((0, -1), (-1, 0), (1, 0), (0, 1)))
                if touch:
                    spr.px[yy * W + xx] = 1
                continue
            if k == 3:
                spr.px[yy * W + xx] = 2
                continue
            cols, off = (bark, ob) if k == 1 else (leafc, ol)
            up = yy > 0 and cells[yy - 1][xx] == k
            lf = xx > 0 and cells[yy][xx - 1] == k
            s = len(cols) - 1 if not up else ((len(cols) - 1) // 2 if lf else max(0, (len(cols) - 1) // 2 - 1))
            spr.px[yy * W + xx] = off + s
    return [spr]
