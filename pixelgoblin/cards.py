"""Character cards — the build bit chain for one character, on one sheet.

A card shows the same genome at every tier, each scaled by a whole number to
the same display height, with the era, colour count and the features that tier
ADDS over the one before. It is the reference an artist or a game uses to keep
one character uniform across resolutions and eras. A JSON twin carries the same
data for programs.
"""

from __future__ import annotations

from . import font, sharecode, typefile
from .gen import rig
from .sprite import TRANSPARENT, Sprite, blit

BG, PANEL, INK, MUTE, ACCENT = (32, 30, 28, 255), (46, 43, 40, 255), (233, 227, 207, 255), (150, 145, 128, 255), (217, 164, 65, 255)
CELL = 128


def card(tf, seed: int, tiers=rig.TIERS, eras=None, title: str | None = None) -> tuple[Sprite, dict]:
    g, chain = rig.chain(tf, seed, tiers, eras)
    code = sharecode.encode(tf.type_hash, seed)
    title = title or typefile.display_name(tf)
    widths = [256 if c["tier"] == 256 else CELL for c in chain]
    W = sum(widths) + 8 * (len(chain) + 1)
    H = 30 + 256 + 70 + 8
    out = Sprite(W, H, [TRANSPARENT, BG, PANEL, INK, MUTE, ACCENT])
    out.px[:] = bytes([1]) * (W * H)
    font.draw(out, 8, 8, title, 5, 2)
    font.draw(out, 8 + font.text_width(title, 2) + 12, 12, f"{tf.id}  SEED {seed}  {code}", 4, 1)
    x = 8
    prev: set = set()
    rows = []
    for c, w in zip(chain, widths):
        spr = c["sprite"]
        k = (CELL if c["tier"] < 256 else 256) // c["tier"] if c["tier"] < 256 else 1
        for yy in range(30, 30 + 256):
            for xx in range(x, x + w):
                out.px[yy * W + xx] = 2
        big = spr.scaled(k) if k > 1 else spr
        blit(out, big, x + (w - big.w) // 2, 30 + 256 - big.h)
        feats = set(c["features"])
        added = sorted(feats - prev)
        prev |= feats
        font.draw(out, x, 30 + 256 + 6, f"{c['tier']}PX  {c['era']}", 3, 1)
        font.draw(out, x, 30 + 256 + 14, f"{c['colors']} COLOURS", 4, 1)
        line, ly = "", 30 + 256 + 24
        for f in ["+" + a.replace("_", " ").replace(".", " ") for a in added]:
            if font.text_width(line + " " + f) > w and line:
                font.draw(out, x, ly, line, 4, 1)
                line, ly = "", ly + 7
            line = (line + " " + f).strip()
        if line and ly < H - 6:
            font.draw(out, x, ly, line, 4, 1)
        rows.append({"tier": c["tier"], "era": c["era"], "era_rule": rig.ERAS[c["era"]]["why"], "colors": c["colors"],
                     "features": c["features"], "adds": added, "pixel_hash": spr.pixel_hash()})
        x += w + 8
    data = {"id": tf.id, "label": title, "seed": seed, "share": code, "type_hash": tf.type_hash,
            "genome": g, "chain": rows, "lod_ladder": rig.LOD}
    return out, data


# ---------------------------------------------------------------- labelled sheets
LIGHT_BG, LIGHT_INK, LIGHT_MUTE = (236, 230, 212, 255), (38, 38, 30, 255), (106, 101, 82, 255)


def labelled(items: list[tuple[str, Sprite]], cell: int, cols: int, label_rows: int = 1, dark: bool = False) -> Sprite:
    """Sprites bottom-aligned in equal cells, each with a caption underneath."""
    lab_h = 7 * label_rows + 3
    rows = (len(items) + cols - 1) // cols
    W, H = cols * (cell + 6) + 6, rows * (cell + lab_h + 6) + 6
    bg, ink, mute = (BG, INK, MUTE) if dark else (LIGHT_BG, LIGHT_INK, LIGHT_MUTE)
    out = Sprite(W, H, [TRANSPARENT, bg, ink, mute])
    out.px[:] = bytes([1]) * (W * H)
    for i, (label, s) in enumerate(items):
        x0, y0 = 6 + (i % cols) * (cell + 6), 6 + (i // cols) * (cell + lab_h + 6)
        blit(out, s, x0 + (cell - s.w) // 2, y0 + cell - s.h)
        for k, line in enumerate(label.split("\n")[:label_rows]):
            while font.text_width(line) > cell and len(line) > 1:
                line = line[:-1]
            font.draw(out, x0 + (cell - font.text_width(line)) // 2, y0 + cell + 3 + 7 * k, line, 2 if k == 0 else 3)
    return out


def labelled_pages(items: list[tuple[str, Sprite]], cell: int, cols: int, label_rows: int = 1, dark: bool = False) -> list[Sprite]:
    """Like labelled, but split over several sheets when the sprites together need more than
    256 colours (an indexed PNG's limit). Order is kept; each page is as full as it can be."""
    pages, start = [], 0
    while start < len(items):
        lo, hi = start + 1, len(items)
        best = lo
        while lo <= hi:  # the longest run from `start` that fits in one palette
            mid = (lo + hi) // 2
            colours = set()
            for _, sp in items[start:mid]:
                colours.update(sp.palette[1:])
            if len(colours) <= 250:
                best, lo = mid, mid + 1
            else:
                hi = mid - 1
        pages.append(labelled(items[start:best], cell, cols, label_rows, dark))
        start = best
    return pages


def expressions(tf, seed: int, tier: int = 64, era: str | None = None) -> list[tuple[str, Sprite]]:
    """The same face with every expression. Only the expression field changes."""
    g = rig.genome(tf.data, rig.streams_for(tf, seed))
    return [(e, rig.render(tf.data, dict(g, expression=e), tier, era)[0]) for e in rig.EXPRESSIONS]


def team_row(tf, seed: int, tier: int = 64, era: str | None = None) -> list[tuple[str, Sprite]]:
    """The same character in every clan's colours."""
    from . import typefile
    out = [("own colours", rig.render(tf.data, rig.genome(tf.data, rig.streams_for(tf, seed)), tier, era)[0])]
    for name, spec in sorted(typefile.teams().items()):
        t = typefile.with_team(tf, name)
        out.append((spec.get("label", name), rig.render(t.data, rig.genome(t.data, rig.streams_for(t, seed)), tier, era)[0]))
    return out


def zoom(tf, seed: int, from_tier: int = 16, to_tier: int = 256, steps: int = 24, eras=None) -> list[Sprite]:
    """A crowd goblin zooming into its portrait: every frame dissolves between
    the two chain tiers around its size (ordered dither), scaled to whole
    screen pixels and standing on the same ground line."""
    g = rig.genome(tf.data, rig.streams_for(tf, seed))
    cache = {}

    def at(t):
        if t not in cache:
            cache[t] = rig.render(tf.data, g, t, (eras or {}).get(t))[0]
        return cache[t]
    frames = []
    for size, a, b, w in rig.zoom_plan(from_tier, to_tier, steps):
        out = Sprite(to_tier, to_tier, [TRANSPARENT])
        A, B = at(a), at(b)
        ox, oy = (to_tier - size) // 2, to_tier - size
        for y in range(size):
            for x in range(size):
                use_b = w > rig.BAYER4[y % 4][x % 4]
                src = B if use_b else A
                i = src.px[(y * src.h // size) * src.w + x * src.w // size]
                if i:
                    out.set(ox + x, oy + y, out.color_index(src.palette[i]))
        frames.append(out)
    return frames
