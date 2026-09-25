"""Squint — does the sprite still read at 1x, on the backgrounds it will sit on?

Three plain checks, reported separately (never merged into one score):

  contrast    the silhouette's edge against the background, as a WCAG-style
              contrast ratio; 3:1 is the floor for "you can see where it ends"
  detail      how many distinct colours survive a 1-pixel squint (neighbour
              averaging), as a share of the colours drawn
  mass        how much of the canvas the sprite fills; under 15% tends to vanish
"""

from __future__ import annotations

from .color import rel_luminance

BACKGROUNDS = {"light": (236, 232, 218), "dark": (24, 22, 26), "grass": (74, 106, 46), "stone": (120, 118, 112)}


def _ratio(a: float, b: float) -> float:
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def squint(spr, backgrounds=None) -> dict:
    W, H = spr.w, spr.h
    edge = []
    for y in range(H):
        for x in range(W):
            i = spr.px[y * W + x]
            if i and any(spr.get(x + dx, y + dy) == 0 for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1))):
                edge.append(rel_luminance(spr.palette[i]))
    out = {"contrast": {}, "detail": 0, "mass": 0}
    for name, rgb in (backgrounds or BACKGROUNDS).items():
        bl = rel_luminance(rgb)
        if not edge:
            out["contrast"][name] = {"ratio": 0.0, "reads": False}
            continue
        worst = sorted(_ratio(e, bl) for e in edge)[len(edge) // 10]  # 10th percentile edge pixel
        out["contrast"][name] = {"ratio": round(worst, 2), "reads": worst >= 3.0}
    drawn = {i for i in spr.px if i}
    blurred = set()
    for y in range(H):
        for x in range(W):
            if spr.px[y * W + x]:
                acc = [0, 0, 0]
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        j = spr.get(x + dx, y + dy)
                        if j:
                            c = spr.palette[j]
                            acc = [acc[k] + c[k] for k in range(3)]
                            n += 1
                blurred.add(tuple(v // n // 24 for v in acc))
    out["detail"] = min(100, len(blurred) * 100 // max(1, len(drawn)))
    out["mass"] = sum(1 for i in spr.px if i) * 100 // (W * H)
    return out
