#!/usr/bin/env python3
"""Derive material ramps from reference images (tool-time; floats allowed).

Each material is a hue window in OKLab plus a minimum chroma. Pixels in the
window are sorted by lightness and five quantile bands are averaged, giving a
dark-to-light ramp. The output records the source images' SHA-256 so the
ramps can be traced back to the exact pictures they came from.

usage: extract_ramps.py IMAGE [IMAGE ...] > ramps.json
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pixelgoblin.color import oklab_to_rgb, rgb_to_oklab  # noqa: E402
from pixelgoblin.png import read  # noqa: E402

WINDOWS = {  # name: (hue from, hue to, minimum chroma)
    "skin": (95, 130, 0.05), "red_cloth": (5, 40, 0.08), "purple_cloth": (290, 345, 0.06),
    "sky": (215, 265, 0.05), "brass": (70, 95, 0.07), "leather": (40, 70, 0.05), "arcane": (265, 300, 0.08),
}


def pixels(path: str, width: int = 384):
    w, h, rgba = read(path)
    step = max(1, w // width)
    for y in range(0, h, step):
        for x in range(0, w, step):
            i = (y * w + x) * 4
            yield rgba[i:i + 3]


def main(paths: list[str]) -> dict:
    labs = [rgb_to_oklab(c) for p in paths for c in pixels(p)]
    out = {"sources": {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}, "ramps": {}}
    for name, (h0, h1, cmin) in WINDOWS.items():
        sel = sorted(l for l in labs if math.hypot(l[1], l[2]) >= cmin and 0.2 < l[0] < 0.95
                     and h0 <= (math.degrees(math.atan2(l[2], l[1])) + 360) % 360 < h1)
        n = len(sel)
        if n < 50:
            continue
        ramp = []
        for q in (0.08, 0.28, 0.5, 0.72, 0.92):
            chunk = sel[int(n * max(0, q - 0.08)):int(n * min(1, q + 0.08))]
            avg = tuple(sum(p[i] for p in chunk) / len(chunk) for i in range(3))
            ramp.append("#%02x%02x%02x" % oklab_to_rgb(avg))
        out["ramps"][name] = {"pixels": n, "colors": ramp}
    return out


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):  # a pipe on Windows defaults to cp1252; write UTF-8 everywhere
        _s.reconfigure(encoding="utf-8")
    print(json.dumps(main(sys.argv[1:]), indent=1))
