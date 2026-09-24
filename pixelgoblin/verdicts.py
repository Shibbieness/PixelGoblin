"""Two verdicts, never merged (ported from SPIRE).

  SPEC verdict   — did the generator do what the type file says?
  TARGET verdict — can the destination platform actually use it?

Merging them would blame a type file for a platform limit ("your goblin is
wrong") when the truth is "the NES cannot show five colours in one sprite".
There is deliberately no combined field anywhere in this API.
"""

from __future__ import annotations

from . import palettes

TARGETS = {
    "modern":  {"max_colors": 255, "multiple_of": 1, "max_size": 4096, "palette": None,
                "why": "any modern engine; only the 256-entry indexed limit applies"},
    "pico8":   {"max_colors": 16, "multiple_of": 1, "max_size": 128, "palette": "pico8",
                "why": "PICO-8 shows only its fixed 16 colours on a 128x128 screen"},
    "gameboy": {"max_colors": 3, "multiple_of": 8, "max_size": 160, "palette": None,
                "why": "Game Boy sprites use 3 shades plus transparent, built from 8x8 tiles"},
    "nes":     {"max_colors": 3, "multiple_of": 8, "max_size": 256, "palette": None,
                "why": "each NES sprite palette has 3 colours plus transparent, in 8x8 tiles"},
}


def spec_verdict(tf, spr) -> dict:
    d = tf.data
    checks = []
    W, H = d["size"]
    checks.append(("size", (spr.w, spr.h) == (W, H), f"{spr.w}x{spr.h} vs type file {W}x{H}"))
    if "max_colors" in d:
        n = spr.used_colors()
        checks.append(("max_colors", n <= d["max_colors"], f"{n} used, limit {d['max_colors']}"))
    if d.get("generator") == "mask":
        edge_ok = {1}
        off = 3
        for r in d["palette"]["ramps"]:
            edge_ok.add(off)  # selout uses each ramp's darkest colour
            off += len(r["colors"])
        bad = sum(1 for y in range(spr.h) for x in range(spr.w)
                  if spr.px[y * spr.w + x] and spr.px[y * spr.w + x] not in edge_ok
                  and any(spr.get(x + a, y + b) == 0 for a, b in ((0, -1), (-1, 0), (1, 0), (0, 1))))
        checks.append(("outline", bad == 0, f"{bad} silhouette pixels without an outline colour"))
        if d.get("mirror"):
            body = d["body"]
            ax = body["anchor"][0]
            fw = len(body["template"][0]) * 2
            ok = all((spr.px[y * spr.w + x] != 0) == (spr.px[y * spr.w + (2 * ax + fw - 1 - x)] != 0)
                     for y in range(spr.h) for x in range(spr.w) if 0 <= 2 * ax + fw - 1 - x < spr.w)
            checks.append(("mirror", ok, "silhouette symmetric about the body box"))
    return {"verdict": "SOUND" if all(c[1] for c in checks) else "UNSOUND",
            "checks": [{"name": n, "ok": ok, "detail": det} for n, ok, det in checks]}


def target_verdict(spr, target: str) -> dict:
    if target not in TARGETS:
        raise ValueError(f"unknown target {target!r}; choose one of {sorted(TARGETS)}")
    t = TARGETS[target]
    checks = []
    n = spr.used_colors()
    checks.append(("colors", n <= t["max_colors"], f"{n} colours used, {target} allows {t['max_colors']}"))
    m = t["multiple_of"]
    checks.append(("tile_grid", spr.w % m == 0 and spr.h % m == 0, f"{spr.w}x{spr.h} must be multiples of {m}"))
    checks.append(("max_size", spr.w <= t["max_size"] and spr.h <= t["max_size"], f"limit {t['max_size']}"))
    if t["palette"]:
        allowed = {c[:3] for c in palettes.get(t["palette"])}
        used = {spr.palette[i][:3] for i in spr.px if i}
        off = sorted(used - allowed)
        checks.append(("fixed_palette", not off, f"{len(off)} colours outside the {t['palette']} palette"))
    return {"verdict": "FITS" if all(c[1] for c in checks) else "DOES_NOT_FIT", "target": target, "why": t["why"],
            "checks": [{"name": n_, "ok": ok, "detail": det} for n_, ok, det in checks]}
