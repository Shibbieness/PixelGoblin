"""Character cards — the build bit chain for one character, on one sheet.

A card shows the same genome at every tier, each scaled by a whole number to
the same display height, with the era, colour count and the features that tier
ADDS over the one before. It is the reference an artist or a game uses to keep
one character uniform across resolutions and eras. A JSON twin carries the same
data for programs.
"""

from __future__ import annotations

from . import font, sharecode
from .gen import rig
from .sprite import TRANSPARENT, Sprite, blit

BG, PANEL, INK, MUTE, ACCENT = (32, 30, 28, 255), (46, 43, 40, 255), (233, 227, 207, 255), (150, 145, 128, 255), (217, 164, 65, 255)
CELL = 128


def card(tf, seed: int, tiers=rig.TIERS, eras=None, title: str | None = None) -> tuple[Sprite, dict]:
    g, chain = rig.chain(tf, seed, tiers, eras)
    code = sharecode.encode(tf.type_hash, seed)
    title = title or tf.data.get("label") or tf.id
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
