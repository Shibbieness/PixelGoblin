"""Exports: sprite sheets + Aseprite-style JSON, contact sheets, and the
longevity export (a sprite readable with no program at all).

Every export carries a provenance record. Provenance is deterministic — no
timestamps — so a re-export is byte-identical to the original and an
archivist can tell a re-export from a change.
"""

from __future__ import annotations

import json

from . import CREDIT, ENGINE_MAJOR, VERSION
from .sprite import TRANSPARENT, Sprite, blit, rgba_to_hex

SYMBOLS = ".abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def provenance(tf=None, seed=None, **extra) -> dict:
    rec = {"engine": "PixelGoblin", "version": VERSION, "engine_major": ENGINE_MAJOR,
           "credit": CREDIT, "ml_used": False}
    if tf is not None:
        rec.update({"type_id": tf.id, "type_hash": tf.type_hash, "license": tf.license, "generator": tf.generator})
    if seed is not None:
        rec["seed"] = seed
    rec.update(extra)
    return rec


def sheet(frames: list[Sprite], name: str, frame_ms: int, image_name: str, prov: dict, tags=None) -> tuple[Sprite, dict]:
    """Horizontal strip + JSON in the widely-read Aseprite 'hash' layout."""
    w, h = frames[0].w, frames[0].h
    out = Sprite(w * len(frames), h, [TRANSPARENT])
    meta_frames = {}
    for i, f in enumerate(frames):
        blit(out, f, i * w, 0)
        meta_frames[f"{name} {i}"] = {"frame": {"x": i * w, "y": 0, "w": w, "h": h}, "rotated": False, "trimmed": False,
                                      "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h},
                                      "sourceSize": {"w": w, "h": h}, "duration": frame_ms}
    data = {"frames": meta_frames,
            "meta": {"app": "PixelGoblin", "version": VERSION, "image": image_name, "format": "RGBA8888",
                     "size": {"w": out.w, "h": out.h}, "scale": "1",
                     "frameTags": tags or [{"name": "idle", "from": 0, "to": len(frames) - 1, "direction": "forward"}],
                     "provenance": prov}}
    return out, data


def contact_sheet(sprites: list[Sprite], cols: int = 8, gap: int = 1) -> Sprite:
    w = max(s.w for s in sprites)
    h = max(s.h for s in sprites)
    rows = (len(sprites) + cols - 1) // cols
    out = Sprite(cols * (w + gap) + gap, rows * (h + gap) + gap, [TRANSPARENT])
    for i, s in enumerate(sprites):
        blit(out, s, gap + (i % cols) * (w + gap), gap + (i // cols) * (h + gap))
    return out


def ascii_export(s: Sprite, title: str, prov: dict) -> str:
    """Printable ASCII, self-describing in prose, no escaping, no references.
    Readable in three hundred years with nothing but eyes."""
    if len(s.palette) > len(SYMBOLS):
        raise ValueError("too many colours for the ASCII export (limit 63)")
    lines = [
        f"PIXEL IMAGE: {title}",
        "",
        "This text is a small picture. It is a grid of characters. Each",
        "character is one square dot of colour. Rows run top to bottom,",
        "dots run left to right. The table below says which colour each",
        "character stands for, as red, green and blue amounts from 0 to 255.",
        "A full stop (.) means no colour: the dot is see-through.",
        "",
        f"WIDTH {s.w}",
        f"HEIGHT {s.h}",
        "",
        "COLOURS",
    ]
    for i, c in enumerate(s.palette):
        if i == 0:
            continue
        lines.append(f"{SYMBOLS[i]} red {c[0]} green {c[1]} blue {c[2]}")
    lines += ["", "PICTURE"]
    for y in range(s.h):
        lines.append("".join(SYMBOLS[s.px[y * s.w + x]] for x in range(s.w)))
    lines += ["", "MADE BY"]
    for k in sorted(prov):
        lines.append(f"{k} {prov[k]}")
    lines.append("END")
    return "\n".join(lines) + "\n"


def ascii_import(text: str) -> Sprite:
    lines = text.splitlines()
    w = int(next(l for l in lines if l.startswith("WIDTH ")).split()[1])
    h = int(next(l for l in lines if l.startswith("HEIGHT ")).split()[1])
    ci = lines.index("COLOURS")
    pal = [TRANSPARENT]
    sym = {".": 0}
    i = ci + 1
    while lines[i].strip():
        p = lines[i].split()
        sym[p[0]] = len(pal)
        pal.append((int(p[2]), int(p[4]), int(p[6]), 255))
        i += 1
    pi = lines.index("PICTURE")
    s = Sprite(w, h, pal)
    for y in range(h):
        row = lines[pi + 1 + y]
        for x in range(w):
            s.px[y * w + x] = sym[row[x]]
    return s


def palette_json(s: Sprite) -> str:
    return json.dumps([rgba_to_hex(c) for c in s.palette[1:]])
