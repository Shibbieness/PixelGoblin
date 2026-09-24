"""Image + tag -> pixel art (TOOL-TIME: floats allowed, output saved as pixels).

The tag picks a conversion profile from types/tags.toml, inheriting through
dotted parents (creature -> creature.small). Pipeline:

  load -> alpha crop -> downsample -> palette (fixed or seeded k-means in
  OKLab) -> dither -> cleanup (orphans, pixel-perfect) -> outline

`likeness()` goes one step further: it turns a converted image into a mask
type file, so one example becomes a generator for more things like it.
"""

from __future__ import annotations

from collections import Counter

from . import palettes
from .color import dist2, oklab_to_rgb, rgb_to_oklab
from .png import read as read_png
from .sprite import TRANSPARENT, Sprite, rgba_to_hex
from .typefile import profile_for

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
METHODS = ("nearest", "box", "mode", "median")


def _crop(w, h, rgba, cut=128):
    xs = [p % w for p in range(w * h) if rgba[p * 4 + 3] >= cut]
    if not xs:
        return None
    ys = [p // w for p in range(w * h) if rgba[p * 4 + 3] >= cut]
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    out = bytearray()
    for y in range(y0, y1):
        out += rgba[(y * w + x0) * 4:(y * w + x1) * 4]
    return x1 - x0, y1 - y0, bytes(out)


def downsample(w, h, rgba, tw, th, method="mode"):
    """Returns list of (r,g,b) or None (transparent) per target cell."""
    if method not in METHODS:
        raise ValueError(f"downsample method {method!r}; choose one of {METHODS}")
    cells = []
    for ty in range(th):
        y0, y1 = ty * h // th, max(ty * h // th + 1, (ty + 1) * h // th)
        for tx in range(tw):
            x0, x1 = tx * w // tw, max(tx * w // tw + 1, (tx + 1) * w // tw)
            px = [rgba[(y * w + x) * 4:(y * w + x) * 4 + 4] for y in range(y0, y1) for x in range(x0, x1)]
            opaque = [p for p in px if p[3] >= 128]
            if len(opaque) * 2 < len(px):
                cells.append(None)
                continue
            if method == "nearest":
                c = rgba[(((y0 + y1) // 2) * w + (x0 + x1) // 2) * 4:][:3]
                cells.append(tuple(c) if len(c) == 3 else tuple(opaque[0][:3]))
            elif method == "box":
                n = len(opaque)
                cells.append(tuple(sum(p[i] for p in opaque) // n for i in range(3)))
            elif method == "median":
                cells.append(tuple(sorted(p[i] for p in opaque)[len(opaque) // 2] for i in range(3)))
            else:
                q = Counter((p[0] >> 4, p[1] >> 4, p[2] >> 4) for p in opaque)
                top = max(q.values())
                key = next(k for k in q if q[k] == top)
                sel = [p for p in opaque if (p[0] >> 4, p[1] >> 4, p[2] >> 4) == key]
                n = len(sel)
                cells.append(tuple(sum(p[i] for p in sel) // n for i in range(3)))
    return cells


def kmeans(colors, k, iters=12):
    """Seeded-free deterministic k-means in OKLab: farthest-point init from
    the most frequent colour, fixed iterations, output sorted dark->light."""
    labs = [rgb_to_oklab(c) for c in colors]
    uniq = sorted(set(labs))
    if len(uniq) <= k:
        return sorted({tuple(c) for c in colors}, key=lambda c: rgb_to_oklab(c)[0])
    freq = Counter(labs)
    centers = [max(uniq, key=lambda p: (freq[p], p))]
    while len(centers) < k:
        centers.append(max(uniq, key=lambda p: (min(dist2(p, c) for c in centers), p)))
    for _ in range(iters):
        groups = [[] for _ in centers]
        for p in labs:
            groups[min(range(len(centers)), key=lambda i: dist2(p, centers[i]))].append(p)
        centers = [tuple(sum(v[j] for v in g) / len(g) for j in range(3)) if g else centers[i] for i, g in enumerate(groups)]
    out = sorted({oklab_to_rgb(c) for c in centers}, key=lambda c: rgb_to_oklab(c)[0])
    return out


def _nearest(lab, pal_labs):
    return min(range(len(pal_labs)), key=lambda i: dist2(lab, pal_labs[i]))


def is_l_corner(s: Sprite, x: int, y: int, c: int) -> bool:
    """A stroke pixel is an L-corner when it has exactly one horizontal and one
    vertical same-colour neighbour, those two touch diagonally (so removing it
    keeps the stroke connected), the fourth cell of that 2x2 square is empty
    (so it is a stroke, not a filled block), and it has at most one other
    same-colour neighbour (the stroke continuing)."""
    same = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx or dy) and s.get(x + dx, y + dy) == c]
    hz = [n for n in same if n[1] == 0]
    vt = [n for n in same if n[0] == 0]
    if len(hz) != 1 or len(vt) != 1 or len(same) > 3:
        return False
    return s.get(x + hz[0][0], y + vt[0][1]) != c


def pixel_perfect(s: Sprite, index: int | None = None) -> int:
    """Remove L-corners from 1-pixel strokes (the pixel-perfect stroke habit).
    Scans in order and updates live, so a staircase keeps every other step.
    Returns pixels removed."""
    removed = 0
    for y in range(s.h):
        for x in range(s.w):
            c = s.px[y * s.w + x]
            if c == 0 or (index is not None and c != index):
                continue
            if is_l_corner(s, x, y, c):
                s.px[y * s.w + x] = 0
                removed += 1
    return removed


def count_l_corners(s: Sprite, index: int) -> int:
    return sum(1 for y in range(s.h) for x in range(s.w) if s.get(x, y) == index and is_l_corner(s, x, y, index))


def _remove_orphans(s: Sprite) -> int:
    W, H, fixed = s.w, s.h, 0
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            c = s.px[y * W + x]
            if not c:
                continue
            nb = [s.px[(y + dy) * W + x + dx] for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1))]
            if 0 not in nb and len(set(nb)) == 1 and nb[0] != c:
                s.px[y * W + x] = nb[0]
                fixed += 1
    return fixed


def convert_rgba(w, h, rgba, tag: str, overrides: dict | None = None) -> tuple[Sprite, dict]:
    prof = dict(profile_for(tag))
    prof.update(overrides or {})
    size = int(prof.get("size", 32))
    colors = int(prof.get("colors", 16))
    outline = prof.get("outline", "selout")
    margin = 1 if outline != "none" else 0
    report = {"tag": tag, "profile": prof}
    cropped = _crop(w, h, rgba)
    if cropped is None:
        report["empty"] = True
        return Sprite(size, size), report
    cw, ch, crgba = cropped
    inner = max(1, size - 2 * margin)
    if cw >= ch:
        tw, th = inner, max(1, round(inner * ch / cw))
    else:
        tw, th = max(1, round(inner * cw / ch)), inner
    cells = downsample(cw, ch, crgba, tw, th, prof.get("downsample", "mode"))
    opaque = [c for c in cells if c is not None]
    if not opaque:
        report["empty"] = True
        return Sprite(size, size), report
    pal_name = prof.get("palette", "auto")
    budget = colors - (1 if outline == "dark" else 0)
    if pal_name == "auto":
        pal = kmeans(opaque, max(1, budget))
    else:
        pal = [c[:3] for c in palettes.resolve(pal_name)]
        if len(pal) > colors:
            used = Counter(_nearest(rgb_to_oklab(c), [rgb_to_oklab(p) for p in pal]) for c in opaque)
            pal = [pal[i] for i, _ in sorted(used.items(), key=lambda kv: (-kv[1], kv[0]))[:colors]]
    labs = [rgb_to_oklab(p) for p in pal]
    spr = Sprite(size, size, [TRANSPARENT] + [(r, g, b, 255) for r, g, b in pal])
    ox, oy = (size - tw) // 2, (size - th) // 2
    dither = prof.get("dither", "none")
    err = [[0.0, 0.0, 0.0] for _ in range(tw * th)]
    for y in range(th):
        for x in range(tw):
            c = cells[y * tw + x]
            if c is None:
                continue
            lab = list(rgb_to_oklab(c))
            if dither == "bayer":
                lab[0] += (BAYER4[y % 4][x % 4] - 7.5) / 16 * 0.06
            elif dither == "fs":
                e = err[y * tw + x]
                lab = [lab[i] + e[i] for i in range(3)]
            i = _nearest(lab, labs)
            if dither == "fs":
                q = [lab[j] - labs[i][j] for j in range(3)]
                for dx, dy, wgt in ((1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < tw and ny < th and cells[ny * tw + nx] is not None:
                        for j in range(3):
                            err[ny * tw + nx][j] += q[j] * wgt / 16
            spr.px[(oy + y) * size + ox + x] = i + 1
    report["orphans_fixed"] = _remove_orphans(spr) if prof.get("cleanup", True) else 0
    if outline != "none":
        _outline(spr, outline, labs)
    report["colors_used"] = spr.used_colors()
    return spr, report


def _outline(spr: Sprite, style: str, labs) -> None:
    W, H = spr.w, spr.h
    darkest = 1 + min(range(len(labs)), key=lambda i: labs[i][0])
    marks = []
    for y in range(H):
        for x in range(W):
            if spr.px[y * W + x]:
                continue
            for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                b = spr.get(x + dx, y + dy)
                if b:
                    if style == "selout":
                        L, A, B = labs[b - 1]
                        target = (L * 0.55, A, B)
                        marks.append((x, y, 1 + _nearest(target, labs)))
                    else:
                        marks.append((x, y, darkest))
                    break
    for x, y, i in marks:
        spr.px[y * W + x] = i


def convert_file(path, tag: str, overrides=None):
    w, h, rgba = read_png(path)
    return convert_rgba(w, h, rgba, tag, overrides)


# ---------------------------------------------------------------- likeness

def likeness(spr: Sprite, type_id: str, tag: str, license: str = "AGPL-3.0-or-later") -> str:
    """Turn a (converted) sprite into a mask type file (TOML text) that
    generates things like it. Interior -> '#', edge body -> '1'."""
    W, H = spr.w, spr.h
    solid = [[1 if spr.px[y * W + x] else 0 for x in range(W)] for y in range(H)]
    # peel an outline ring if present (darkest colour on the silhouette edge)
    ys = [y for y in range(H) if any(solid[y])]
    xs = [x for x in range(W) if any(solid[y][x] for y in range(H))]
    if not ys:
        raise ValueError("image has no opaque pixels to learn a shape from")
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    sym = sum(1 for y in range(y0, y1) for x in range(x0, x1) if solid[y][x] == solid[y][x1 - 1 - (x - x0)])
    mirror = sym * 100 >= 85 * (x1 - x0) * (y1 - y0)
    rows = []
    for y in range(y0, y1):
        r = ""
        for x in range(x0, x1):
            if not solid[y][x]:
                r += "."
                continue
            inner = all(0 <= x + dx < W and 0 <= y + dy < H and solid[y + dy][x + dx]
                        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)))
            r += "#" if inner else "1"
        rows.append(r)
    if mirror:
        half = (x1 - x0 + 1) // 2
        rows = [r[:half] for r in rows]
    labs = sorted({spr.palette[i][:3] for i in spr.px if i}, key=lambda c: rgb_to_oklab(c)[0])
    groups: dict[int, list] = {}
    import math
    for c in labs:
        L, A, B = rgb_to_oklab(c)
        hue = int(((math.degrees(math.atan2(B, A)) + 360) % 360) // 60) if (A * A + B * B) ** 0.5 > 0.03 else 6
        groups.setdefault(hue, []).append(c)
    ramps = []
    for hue, cs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(cs) == 1:
            L, A, B = rgb_to_oklab(cs[0])
            cs = [oklab_to_rgb((max(0.0, L - 0.18), A, B)), cs[0]]
        ramps.append((f"h{hue}", len(cs), [rgba_to_hex((*c, 255)) for c in cs[:8]]))
    fw = len(rows[0]) * (2 if mirror else 1)
    size = [max(fw + 2, 8), len(rows) + 2]
    lines = [f'# Learned from an example by `pixelgoblin likeness`. Edit freely.',
             f'schema = "pixelgoblin/type@1"', f'id = "{type_id}"', f'tag = "{tag}"',
             f'generator = "mask"', f'license = "{license}"', f'size = {size}',
             f'mirror = {"true" if mirror else "false"}', 'outline_style = "selout"', '',
             '[palette]', 'outline = "#14101c"', '']
    for name, w, cols in ramps[:4]:
        lines += ['[[palette.ramps]]', f'name = "{name}"', f'weight = {w}', f'colors = {cols}'.replace("'", '"'), '']
    lines += ['[body]', 'anchor = [1, 1]', 'template = [']
    lines += [f'  "{r}",' for r in rows]
    lines += [']', '', '[features]', 'eyes = 0', '', '[animation]', 'frames = 1', 'frame_ms = 200', '']
    return "\n".join(lines)
