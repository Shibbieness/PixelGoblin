"""Mask generator — creatures, items, icons, anything with a silhouette.

Lineage: Dave Bollinger's Pixel Spaceships (2006) cell-mask idea, rewritten
from scratch with PixelGoblin's own masks and rules:

  template cells   .  empty          1  maybe body
                   #  always body    2  body or edge

Layers (body, then each part in order) each draw from their OWN named random
stream, so adding a part to a type file never changes an existing creature's
body (ADR-008). Every step is integer-only and mirrors line-for-line in the
JavaScript port (editor/pixelgoblin.html), which is checked against the same
goldens by build gate B13.
"""

from __future__ import annotations

from .. import ENGINE_MAJOR
from ..rng import M32, Streams, hash32, master_seed
from ..sprite import TRANSPARENT, Sprite, hex_to_rgba

T_OUT, T_EYE, T_BASE = 1, 2, 3


def _streams(tf, seed: int, overrides=None) -> Streams:
    return Streams(master_seed(tf.type_hash, seed, ENGINE_MAJOR), overrides)


def stream_paths(data: dict) -> list[str]:
    return ["body"] + [f"part/{p['name']}" for p in data.get("parts", []) or []] + ["shade", "eyes"]


def build_cells(data: dict, S: Streams):
    W, H = data["size"]
    ramps = data["palette"]["ramps"]
    names = [r["name"] for r in ramps]
    mirror = bool(data.get("mirror", False))
    cells = [[0] * W for _ in range(H)]
    rampof = [[-1] * W for _ in range(H)]
    layers = [("body", data["body"])] + [(f"part/{p['name']}", p) for p in data.get("parts", []) or []]
    for path, L in layers:
        rng = S.rng(path)
        if path != "body" and not rng.chance(L["chance"]):
            continue
        sel = L.get("ramp", "any")
        ri = rng.weighted([r["weight"] for r in ramps]) if sel == "any" else names.index(sel)
        t = L["template"]
        ax, ay = L["anchor"]
        tw = len(t[0])
        fw = tw * 2 if mirror else tw
        for y in range(len(t)):
            row = t[y]
            for x in range(tw):
                c = row[x]
                if c == ".":
                    continue
                if c == "#":
                    v = 1
                elif c == "1":
                    v = 1 if rng.below(2) == 0 else 0
                else:
                    v = 1 if rng.below(2) == 0 else 2
                if v == 0:
                    continue
                xs = (x, fw - 1 - x) if mirror else (x,)
                for xx in xs:
                    X, Y = ax + xx, ay + y
                    if v == 1:
                        cells[Y][X] = 1
                        rampof[Y][X] = ri
                    elif cells[Y][X] == 0:
                        cells[Y][X] = 2
    # outline: empty cells touching body (4-neighbour)
    for y in range(H):
        for x in range(W):
            if cells[y][x] == 0 and _touch_body(cells, x, y, W, H):
                cells[y][x] = 3  # temp mark so the scan does not cascade
    for y in range(H):
        for x in range(W):
            if cells[y][x] == 3:
                cells[y][x] = 2
            elif cells[y][x] == 2 and not _touch_body(cells, x, y, W, H):
                cells[y][x] = 0  # a pre-marked edge that ended up floating
    return cells, rampof


def _touch_body(cells, x, y, W, H) -> bool:
    return ((y > 0 and cells[y - 1][x] == 1) or (x > 0 and cells[y][x - 1] == 1)
            or (x < W - 1 and cells[y][x + 1] == 1) or (y < H - 1 and cells[y + 1][x] == 1))


def _is_body(cells, x, y, W, H) -> bool:
    return 0 <= x < W and 0 <= y < H and cells[y][x] == 1


def generate(tf, seed: int, overrides=None) -> Sprite:
    return generate_frames(tf, seed, overrides)[0]


def generate_frames(tf, seed: int, overrides=None) -> list[Sprite]:
    data = tf.data
    S = _streams(tf, seed, overrides)
    W, H = data["size"]
    ramps = data["palette"]["ramps"]
    mirror = bool(data.get("mirror", False))
    cells, rampof = build_cells(data, S)

    offsets, pal = [], [TRANSPARENT, hex_to_rgba(data["palette"]["outline"]),
                       hex_to_rgba(data.get("features", {}).get("eye_color", "#f4f4f4"))]
    for r in ramps:
        offsets.append(len(pal))
        pal += [hex_to_rgba(c) for c in r["colors"]]

    body = data["body"]
    bax = body["anchor"][0]
    bfw = len(body["template"][0]) * (2 if mirror else 1)

    def mx(x):  # mirror within the body box
        return 2 * bax + bfw - 1 - x

    tex_seed = S.rng("shade").next()
    spr = Sprite(W, H, pal)
    selout = data.get("outline_style", "selout") == "selout"
    for y in range(H):
        for x in range(W):
            c = cells[y][x]
            if c == 1:
                cols = ramps[rampof[y][x]]["colors"]
                n = len(cols)
                mid = (n - 1) // 2
                if not _is_body(cells, x, y - 1, W, H):
                    s = n - 1
                elif not _is_body(cells, x, y + 1, W, H):
                    s = 0
                elif not _is_body(cells, x - 1, y, W, H):
                    s = min(n - 1, mid + 1)
                elif not _is_body(cells, x + 1, y, W, H):
                    s = max(0, mid - 1)
                else:
                    xx = min(x, mx(x)) if mirror else x
                    h = hash32(tex_seed ^ ((xx * 0x9E3779B1) & M32) ^ ((y * 0x85EBCA6B) & M32))
                    s = min(n - 1, mid + 1) if h % 8 == 0 else mid
                spr.px[y * W + x] = offsets[rampof[y][x]] + s
            elif c == 2:
                idx = T_OUT
                if selout:
                    for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                        if _is_body(cells, x + dx, y + dy, W, H):
                            idx = offsets[rampof[y + dy][x + dx]]
                            break
                spr.px[y * W + x] = idx

    eyes = data.get("features", {}).get("eyes", 0)
    eye_px = []
    if eyes:
        rng = S.rng("eyes")
        rows = [y for y in range(H) if any(cells[y][x] == 1 for x in range(W))]
        top, bot = rows[0], rows[-1]
        b0, b1 = data.get("features", {}).get("eye_band", [0, 60])
        lo, hi = top + (bot - top) * b0 // 100, top + (bot - top) * b1 // 100
        cand = [(x, y) for y in range(H) for x in range(W)
                if cells[y][x] == 1 and lo <= y <= hi
                and all(_is_body(cells, x + dx, y + dy, W, H) for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)))
                and (not mirror or x < bax + bfw // 2)]
        for _ in range(eyes):
            if not cand:
                break
            x, y = cand.pop(rng.below(len(cand)))
            eye_px.append((x, y))
            if mirror:
                eye_px.append((mx(x), y))
        for x, y in eye_px:
            spr.px[y * W + x] = T_EYE

    frames = [spr]
    n = data.get("animation", {}).get("frames", 1)
    for k in range(1, n):
        f = spr.copy()
        if k % 2 == 1:
            _squash(f)
        if k == 2:
            for x, y in eye_px:
                if f.px[y * W + x] == T_EYE:
                    f.px[y * W + x] = T_OUT
        frames.append(f)
    return frames


def _squash(s: Sprite) -> None:
    """Breathing frame: the top half of the content drops one pixel."""
    W, H = s.w, s.h
    rows = [y for y in range(H) if any(s.px[y * W + x] for x in range(W))]
    if len(rows) < 3:
        return
    mid = (rows[0] + rows[-1]) // 2
    for y in range(mid, 0, -1):
        s.px[y * W:(y + 1) * W] = s.px[(y - 1) * W:y * W]
    s.px[0:W] = bytes(W)
