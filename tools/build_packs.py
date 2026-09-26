#!/usr/bin/env python3
"""Build the resource packs in flavors/boc/packs/ from the source catalogs.

usage: build_packs.py [--check]

Sources (flavors/boc/packs/sources/) were extracted from Mark's own read-only
skills: Book of Cities, the Book of Cities Compendium, the Aether Library, and
CRUCIBLE's database. This script turns them into ordinary type files, one pack
per folder, each with a pack.toml manifest that says where every entry came
from. Colours the sources name in words are resolved here, at tool time (ADR-002
allows floats at tool time only); every entry whose colours were inferred rather
than stated is flagged in its file and counted in its manifest.

--check exits 1 if any generated file differs from what is on disk (gate B22).

    —Shibbieness
    —Claude
"""
from __future__ import annotations

import colorsys
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "flavors" / "boc" / "packs"
SRC = PACKS / "sources"
SCHEMA = "pixelgoblin/type@1"
PACK_SCHEMA = "pixelgoblin/pack@1"
LICENSE = "Proprietary"
FORGED = "2026-09-26"

# ---------------------------------------------------------------- colour words
BASE = {
    "red": "#b03a2e", "crimson": "#9a1e2e", "scarlet": "#c42a2a", "vermilion": "#d8462a", "blood": "#7a1018", "rust": "#9a4a24",
    "orange": "#d8782a", "ember": "#d0582a", "flame": "#e0602a", "amber": "#d8962a", "copper": "#b8683a", "terracotta": "#b85a3a",
    "ochre": "#b8862e", "yellow": "#d8c03a", "gold": "#d4a82e", "golden": "#d4a82e", "sand": "#d0b884", "sandy": "#d0b884",
    "tan": "#b89468", "cream": "#e6d6b0", "ivory": "#eee6cc", "bone": "#ddd2b4", "fossil": "#d6ccae", "fair": "#e8c4a4",
    "rosy": "#e0a48c", "ruddy": "#c07a5e", "pink": "#e08aa0", "rose": "#d8708a", "coral": "#e07a6a", "magenta": "#b84a8a",
    "purple": "#6a3a8a", "violet": "#7a4ab0", "lavender": "#a894d0", "heather": "#8a6a9a", "amethyst": "#8a5ab8", "indigo": "#3a3a8a",
    "blue": "#3a64b0", "sea": "#2a6a8a", "ice": "#9ad0e8", "cyan": "#3ab8c8", "turquoise": "#3ab0a0", "teal": "#2a8a84",
    "aquamarine": "#6ad0bc", "mint": "#8ad8a8", "green": "#4a8a3a", "moss": "#5a7a2e", "olive": "#6a6a2e", "kelp": "#4a5a2a",
    "sage": "#8a9a74", "brown": "#6a4428", "chestnut": "#7a3e22", "bay": "#7a4a2a", "dun": "#a08a64", "bark": "#5a3a22",
    "mud": "#5a4630", "peat": "#3e2e20", "loam": "#4a3424", "silt": "#6a5e4a", "grey": "#7a7a80", "gray": "#7a7a80",
    "slate": "#4a5260", "stone": "#7a766e", "ash": "#8a8480", "ashen": "#9a948e", "storm": "#5a6068", "seal": "#6a6664",
    "silver": "#b4b8c0", "white": "#eceae4", "snow": "#f0f4f6", "pearl": "#e8e4dc", "quartz": "#e4e0e8", "star": "#f4f0dc",
    "black": "#1e1a1e", "obsidian": "#1a141e", "smoky": "#2e2a2e", "void": "#1a1026", "midnight": "#1a2040", "bronze": "#9a6a2e",
    "iron": "#5a5654", "browned": "#8a5a38", "sun": "#e6b04a", "rock": "#7a6a5a", "clay": "#a8704a", "glass": "#a8c8c0", "luminous": "#f4f0e0",
}
LIGHTER = {"pale": 0.18, "light": 0.14, "bright": 0.08, "glowing": 0.12, "luminous": 0.14, "radiant": 0.14, "shimmer": 0.12,
           "milky": 0.12, "bleached": 0.16, "hot": 0.06, "phosphorescent": 0.12, "bioluminescent": 0.12, "spectral": 0.14}
DARKER = {"dark": 0.16, "deep": 0.14, "dense": 0.1, "midnight": 0.12, "wet": 0.06, "weathered": 0.04}
DULLER = {"dull": 0.35, "dusty": 0.3, "muddy": 0.35, "murky": 0.35, "sickly": 0.25, "hazy": 0.3, "dry": 0.2, "weathered": 0.2}
IGNORE = {"spotted", "striped", "stripe", "spots", "glossy", "translucent", "iridescent", "clear", "flecks", "with", "lure", "glow",
          "wide", "cold", "electric", "mottled", "speckled", "slimy", "river", "sun", "browned", "green-black", "red-black"}
UNRESOLVED: list[str] = []


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, int(round(c * 255)))):02x}" for c in rgb)


def _rgb(h: str):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def colour(word: str) -> str:
    """A colour phrase ('pale grey-green', 'dark iron with silver flecks') to one hex colour."""
    w = word.lower().strip()
    if re.fullmatch(r"#[0-9a-f]{6}", w):
        return w
    toks = [t for t in re.split(r"[\s/]+", w) if t]
    bases, mods = [], []
    for t in toks:
        parts = t.split("-") if t not in LIGHTER and t not in BASE else [t]
        for q in parts:
            if q in BASE and q not in ("luminous",):
                bases.append(BASE[q])
            elif q in LIGHTER or q in DARKER or q in DULLER:
                mods.append(q)
            elif q == "luminous":
                mods.append(q)
            elif q in IGNORE:
                continue
    ALONE = {"pale": "#e8dcd0", "clear": "#c8d8e0", "translucent": "#c8d8e0", "iridescent": "#b8c8e0", "glossy": "#5a5a64",
             "spotted": "#8a7a5a", "striped": "#8a7a5a", "glowing lure": "#e8f0a0"}
    if not bases and w in ALONE:
        bases = [ALONE[w]]
    if not bases:
        if "luminous" in mods:
            bases = [BASE["luminous"]]
        else:
            UNRESOLVED.append(word)
            h = int(hashlib.sha256(w.encode()).hexdigest()[:6], 16)
            return _hex(colorsys.hls_to_rgb((h % 360) / 360, 0.45, 0.25))
    # blend the colour words it names (grey-green = halfway)
    cs = [_rgb(b) for b in bases]
    rgb = tuple(sum(c[i] for c in cs) / len(cs) for i in range(3))
    h, l, s = colorsys.rgb_to_hls(*rgb)
    for m in mods:
        l = min(0.94, l + LIGHTER.get(m, 0)) if m in LIGHTER else l
        l = max(0.06, l - DARKER.get(m, 0)) if m in DARKER else l
        s = s * (1 - DULLER.get(m, 0)) if m in DULLER else s
    return _hex(colorsys.hls_to_rgb(h, l, s))


def ramp(base: str, n: int = 5, spread: float = 0.34) -> list[str]:
    """Dark to light around one colour, pixel-art style: shadows cooler, lights warmer."""
    h, l, s = colorsys.rgb_to_hls(*_rgb(base))
    out = []
    for i in range(n):
        t = i / (n - 1) - 0.5                    # -0.5 .. 0.5
        li = min(0.95, max(0.05, l + t * spread * 2 * (0.9 if l > 0.7 else 1)))
        hi = (h + (-0.03 if t < 0 else 0.02) * abs(t) * 2) % 1.0
        si = min(1.0, s * (1.08 if t < 0 else 0.92))
        out.append(_hex(colorsys.hls_to_rgb(hi, li, si)))
    return out


# ---------------------------------------------------------------- TOML writing
def _k(k: str) -> str:
    return k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else json.dumps(k)


def _v(x) -> str:
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, str):
        return json.dumps(x, ensure_ascii=False)
    if isinstance(x, dict):
        return "{ " + ", ".join(f"{_k(k)} = {_v(v)}" for k, v in x.items()) + " }"
    if isinstance(x, list):
        if x and all(isinstance(e, str) for e in x) and sum(len(e) for e in x) > 60:
            return "[\n" + "".join(f"  {_v(e)},\n" for e in x) + "]"
        return "[" + ", ".join(_v(e) for e in x) + "]"
    raise TypeError(type(x))


def toml(doc: dict, head: str = "") -> str:
    """Scalars and simple arrays first, then [tables], then [[arrays of tables]]."""
    lines = [f"# {ln}" if ln else "#" for ln in head.splitlines()] if head else []

    def emit(prefix, d):
        simple = {k: v for k, v in d.items() if not isinstance(v, dict) and not (isinstance(v, list) and v and all(isinstance(e, dict) for e in v) and k in AOT)}
        for k, v in simple.items():
            lines.append(f"{_k(k)} = {_v(v)}")
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append("")
                lines.append(f"[{prefix}{k}]")
                emit(f"{prefix}{k}.", v)
        for k, v in d.items():
            if isinstance(v, list) and v and all(isinstance(e, dict) for e in v) and k in AOT:
                for e in v:
                    lines.append("")
                    lines.append(f"[[{prefix}{k}]]")
                    emit(f"{prefix}{k}.", e)
    emit("", doc)
    return "\n".join(lines).rstrip() + "\n"


AOT = {"ramps", "parts", "layers", "entities", "catalog"}


def head_doc(tid: str, tag: str, gen: str, size, label: str, source: str, inferred: bool) -> dict:
    d = {"schema": SCHEMA, "id": tid, "tag": tag, "generator": gen, "license": LICENSE, "size": list(size), "label": label}
    d["provenance"] = {"source": source, "colors": "inferred from the name (the source states none)" if inferred else "as stated in the source"}
    return d


# ---------------------------------------------------------------- templates (half width; mirrored)
def upscale(t: list[str], k2: int) -> list[str]:
    """Nearest-neighbour scale a template by k2/2 (3 = x1.5, 4 = x2)."""
    H, W = len(t), len(t[0])
    out = []
    for y in range(H * k2 // 2):
        sy = y * 2 // k2
        out.append("".join(t[sy][x * 2 // k2] for x in range(W * k2 // 2)))
    return out


FAUNA = {
    "quadruped": ["..1....", "..#1...", "...####", "..2####", "..#####", "...####", "....###", "..2####", ".2#####", ".######", ".##.###", ".##..#.", ".1#...."],
    "bird": ["......#", ".....##", "1...###", "#2..###", "##2####", ".######", "..#####", "....###", ".....#."],
    "insect": ["..1....", "...1...", "....###", "1..####", ".#.####", "..#####", "1.#####", ".######", "1.#####", "..#####", "...####", "....###"],
    "serpent": ["...####", "..#####", ".##..##", ".##....", ".2#####", "..#####", "....###", ".##..##", ".######", "..2####"],
    "fish": ["......#", ".....##", "....###", "...####", "..#####", "..#####", "...####", "....###", ".....##", "....###", "...1.##"],
    "amphibian": ["..##..#", "..#####", "...####", "..#####", ".######", "#.#####", "#..####", "##.####", ".#..###"],
    "slime": ["....111", "...1222", "..12###", ".12####", ".1#####", "12#####", "12#####", ".1#####", "..12###", "...1111"],
    "other": ["..1..1.", "..#2.##", "..#####", ".2#####", ".######", "12#####", "1######", ".######", ".##.###", ".##..##"],
}
FAUNA_PARTS = {
    "quadruped": [("horns", 35, [2, 0], ["1..", "#1.", ".#."])],
    "bird": [("crest", 50, [6, 0], [".1", "1#"])],
    "insect": [("shell", 60, [4, 3], ["..#", ".##", "###", "###", ".##"])],
    "fish": [("fins", 70, [1, 4], ["1..", "#1.", ".#."])],
    "other": [("spines", 50, [3, 1], ["1.1", "#.#"])],
}
FUNGI = {
    "round": ["....111", "..12###", ".1#####", "12#####", "1######", ".11####"],
    "flat": ["...1111", "12#####", "1######", ".11####"],
    "conical": ["......#", ".....##", "....1##", "...####", "..#####", ".1#####"],
    "shelf": ["1######", "##2####", ".1#####", "..1111."],
    "puffball": ["...####", "..#####", ".######", ".######", "..#####", "...1111"],
    "coral": ["1..1..#", "#1.#1.#", ".#.#.##", ".##.###", "..#####", "...####"],
    "cluster": ["11..11.", "##1.##1", "##..##.", "1...1..", "#..#1..", "#.###.."],
}
ORE_CHUNK = ["...1###", "..#####", ".######", "1######", "#######", "1######", ".######", "..1####"]
ORE_VEIN = ["..#....", ".##.#..", "..#.##.", "....#.."]
ORE_CRYSTAL = ["......#", ".....##", "....1##", "...####", "..#####", "..#####", "...####", "....###", ".....##"]
ORE_ROUND = ["...####", "..#####", ".######", ".######", ".######", "..#####", "...####"]
SIZE_OF = {"tiny": (16, 16, 2), "small": (16, 16, 2), "medium": (20, 20, 3), "large": (24, 24, 3), "huge": (32, 32, 4)}

LSYS = {  # form -> (size, axiom, rules, iterations, step, leaf_radius, trunk_width, fruit_chance)
    "tree": ((40, 48), "FFX", {"X": [{"to": "F[+X][-X]FX", "weight": 3}, {"to": "F[+X]F[-X]X", "weight": 2}, {"to": "FF[++X][-X]X", "weight": 1}]}, 4, [2, 3], 2, 2, 10),
    "shrub": ((32, 32), "FX", {"X": [{"to": "F[+X][-X]FX", "weight": 3}, {"to": "F[+X]FX", "weight": 2}, {"to": "F[-X]FX", "weight": 2}]}, 3, [2, 4], 2, 2, 25),
    "flower": ((16, 24), "FFX]", {"X": [{"to": "F[+FL]FX", "weight": 2}, {"to": "F[-FL]FX", "weight": 2}, {"to": "FFX", "weight": 1}]}, 2, [1, 2], 2, 1, 60),
    "grass": ((16, 16), "X", {"X": [{"to": "F[+FX][-FX]", "weight": 2}, {"to": "F[+FX]FX", "weight": 1}, {"to": "F[-FX]FX", "weight": 1}]}, 2, [1, 2], 0, 1, 10),
    "reed": ((16, 24), "FX]", {"X": [{"to": "FF[+FF]X", "weight": 1}, {"to": "FF[-FF]X", "weight": 1}, {"to": "FFX", "weight": 2}]}, 3, [2, 3], 1, 1, 100),
    "vine": ((24, 40), "FX", {"X": [{"to": "F+F[-L]X", "weight": 2}, {"to": "F-F[+L]X", "weight": 2}, {"to": "FF[+X]X", "weight": 1}]}, 4, [2, 3], 1, 1, 30),
    "cactus": ((24, 32), "FFX", {"X": [{"to": "F[++FF]FX", "weight": 1}, {"to": "F[--FF]FX", "weight": 1}, {"to": "FFX", "weight": 1}]}, 3, [2, 3], 1, 2, 20),
    "crop": ((16, 24), "FX]", {"X": [{"to": "F[+FL][-FL]X", "weight": 2}, {"to": "FFX", "weight": 1}]}, 3, [2, 3], 1, 1, 80),
}

HAIR_EXTRA = {"blond": ramp("#d8b860"), "grey": ramp("#8a8884"), "silver": ramp("#c4c8d0"), "auburn": ramp("#8a3a22"),
              "moss": ramp("#4a6a2a"), "sea": ramp("#2a6a7a"), "gold": ramp("#d4a82e")}
IRIS_EXTRA = {"brown": ["#2a160a", "#5a3418", "#8a5a2e"], "blue": ["#14284a", "#2e5aa0", "#6a9ae0"], "silver": ["#4a4e58", "#8a90a0", "#d0d4e0"]}


# ---------------------------------------------------------------- packs
def load(name: str):
    return json.loads((SRC / name).read_text())


def race_overlay(r: dict, by_id: dict) -> tuple[str, dict]:
    base = by_id.get(r.get("variant_of")) if r.get("variant_of") else None
    get = lambda k, d=None: r.get(k) or (base or {}).get(k) or d
    height, build, ears = get("height", "medium"), get("build", "average"), get("ears", "round")
    goblinish = r["id"].endswith("goblin") or r.get("variant_of") == "goblin" or r["id"] == "goblin"
    stature = {"tiny": [62, 70], "short": [96, 104], "medium": [112, 118], "tall": [119, 124], "huge": [123, 125]}[height]
    sp: dict = {}
    if not goblinish:
        sp["stature"] = stature
    sp["build"] = {"slight": ["slim", "average"], "average": ["average", "slim"], "stocky": ["stocky", "average"], "heavy": ["heavy", "stocky"]}[build]
    if not goblinish:
        sp["ear_len"], sp["ear_lift"], sp["ear_w"] = {"none": ([4, 8], [-4, 2], [20, 24]), "round": ([18, 26], [-6, 4], [22, 28]),
                                                      "pointed": ([52, 78], [4, 20], [24, 30]), "long": ([90, 130], [-10, 30], [28, 36]),
                                                      "fins": ([34, 48], [-4, 10], [26, 32])}[ears]
        sp["nose"] = {"slight": [66, 86], "average": [74, 96], "stocky": [94, 120], "heavy": [104, 136]}[build]
        sp["head_w"] = {"slight": [92, 100], "average": [96, 104], "stocky": [104, 112], "heavy": [106, 116]}[build]
        sp["eye"] = [92, 108]
    feats = set(r.get("features") or []) | set((base or {}).get("features") or [])
    acc = []
    if "beard" in feats:
        acc.append({"item": "beard", "chance": 75})
    if "tusks" in feats or r["id"] in ("orc", "half_orc", "wild_orc", "cave_orc") or r.get("variant_of") == "orc":
        acc.append({"item": "tusks", "chance": 90})
    if {"gills", "scales"} & feats or ears == "fins":
        acc.append({"item": "fins", "chance": 100})
    if r["id"] in ("infernal", "tiefling", "duergar", "drow"):
        acc.append({"item": "tattoo", "chance": 40})
    if acc:
        sp["accessories"] = acc
    rid = r["id"]
    iris = (["red", "amber"] if rid in ("infernal", "tiefling") else ["gold"] if rid == "divine" else ["violet", "silver"] if rid == "drow"
            else ["ice", "blue"] if rid in ("sea_elf", "merfolk", "kuo_toa", "selkie_folk", "coastal_temple_elf", "drowned_hall_dwarf")
            else ["amber", "red", "green", "gold"] if goblinish or r.get("variant_of") == "orc" or rid == "orc"
            else ["brown", "blue", "green", "amber"])
    sp["iris"] = iris
    hair = (["black", "brown", "red", "white"] if goblinish else ["black", "grey"] if "orc" in rid else ["silver", "white"] if rid in ("drow", "divine")
            else ["brown", "red", "black", "grey"] if "dwarf" in rid or rid == "duergar" else ["blond", "silver", "black", "auburn"] if "elf" in rid
            else ["sea", "silver", "black"] if rid in ("merfolk", "kuo_toa", "selkie_folk") else ["brown", "black", "blond", "auburn", "red"])
    sp["hair_color"] = hair
    skins = r.get("skin_colors") or ["tan"]
    doc = {"schema": SCHEMA, "id": f"boc.race.sub.{rid}", "extends": "boc.goblin", "tag": f"creature.humanoid.{rid.replace('_', '-')}",
           "license": LICENSE, "label": r["name"],
           "provenance": {"source": "book-of-cities: races" + (f" (variant of {r['variant_of']})" if r.get("variant_of") else ""),
                          "summary": r.get("summary", ""), "colors": "inferred from the name (the source states none)" if r.get("inferred_colors") else "as stated"},
           "species": sp,
           "palette": {"materials": {"skin": ramp(colour(skins[0]))}, "hair": HAIR_EXTRA, "iris": IRIS_EXTRA}}
    return rid, doc


def biome_types(b: dict) -> list[tuple[str, dict]]:
    sky = [colour(c) for c in (b.get("sky") or ["pale blue"])]
    ground = [colour(c) for c in (b.get("ground") or ["brown"])]
    fol = [colour(c) for c in (b.get("foliage") or ground)]
    top = sky[0]
    skyramp = ramp(top, 5, 0.3)                      # dark to light: deep sky at the top, pale at the horizon
    if b["id"] == "underwater":
        skyramp = list(reversed(skyramp))           # light at the surface, dark in the deep
    inf = bool(b.get("inferred_colors"))
    env = head_doc(f"boc.biome.{b['id']}.sky", "env", "parallax", (160, 90), b["name"] + " sky", f"book-of-cities: biomes ({b['name']})", inf)
    env.update({"stars": 30 if b["id"] in ("tundra", "desert", "badlands") else 0,
                "palette": {"sky": skyramp, "star": "#fff4e0"},
                "layers": [{"name": "far", "colors": ramp(fol[0], 3, 0.2), "base": 60, "periods": [40, 12], "amps": [12, 4], "scroll": 20},
                           {"name": "mid", "colors": ramp(fol[-1], 3, 0.25), "base": 74, "periods": [26, 9], "amps": [8, 3], "scroll": 50},
                           {"name": "ground", "colors": ramp(ground[0], 3, 0.25), "base": 88, "periods": [16, 5], "amps": [3, 2], "scroll": 100}]})
    fill = ramp(ground[-1] if len(ground) > 1 else ground[0], 4, 0.26)
    ter = head_doc(f"boc.biome.{b['id']}.ground", "terrain", "autotile", (16, 16), b["name"] + " ground", f"book-of-cities: biomes ({b['name']})", inf)
    ter.update({"tile": 16, "palette": {"outline": ramp(ground[0], 5)[0], "highlight": ramp(fill[-1], 3)[2], "fill": fill}})
    return [(f"{b['id']}.sky", env), (f"{b['id']}.ground", ter)]


def flora_type(f: dict) -> dict:
    size, axiom, rules, it, step, lr, tw, fc = LSYS.get(f.get("form", "shrub"), LSYS["shrub"])
    cols = [colour(c) for c in (f.get("colors") or ["green"])]
    greens = [c for c in cols if colorsys.rgb_to_hls(*_rgb(c))[0] * 360 in range(60, 170)]
    form = f.get("form", "shrub")
    green = ramp(greens[0] if greens else colour("green"), 4, 0.3)
    petal = next((c for c in cols if c not in greens), cols[0])
    leaf = ramp(petal, 4, 0.34) if form == "flower" else green
    fruit = ramp(petal, 5)[3] if form == "flower" else petal
    stem = ramp(colour("green"), 3, 0.3) if form in ("flower", "grass", "reed", "vine", "cactus", "crop") else ramp(colour("bark brown"), 3, 0.25)
    if form == "cactus":
        stem = ramp(greens[0] if greens else colour("sage"), 3, 0.3)
    d = head_doc(f"boc.flora.{f['id']}", "flora", "lsystem", size, f["name"], "book-of-cities: flora" + (f" ({f['biome']})" if f.get("biome") else ""),
                 bool(f.get("inferred_colors")))
    d.update({"axiom": axiom, "iterations": it, "step": step, "leaf_radius": lr, "fruit_chance": fc, "trunk_width": tw, "rules": rules,
              "palette": {"outline": "#140e14", "fruit": fruit, "bark": stem, "leaf": leaf}})
    if f.get("biome"):
        d["biome"] = f["biome"]
    return d


def mask_doc(tid, tag, size, label, source, inferred, ramps, body, anchor, parts=(), eyes=0, frames=1, outline="#140e14") -> dict:
    d = head_doc(tid, tag, "mask", size, label, source, inferred)
    d.update({"mirror": True, "outline_style": "selout", "palette": {"outline": outline, "ramps": ramps}, "body": {"anchor": anchor, "template": body}})
    if parts:
        d["parts"] = [{"name": n, "chance": c, "anchor": a, "template": t, **({"ramp": r} if r else {})} for n, c, a, t, r in parts]
    d["features"] = {"eyes": eyes} if not eyes else {"eyes": eyes, "eye_color": "#f4ecd0"}
    # icons of one thing (an ore, a mushroom) are meant to look alike: gate B03 holds them to 70 of 100 distinct, creatures to 80
    d["variety_min"] = 70 if tag in ("ore", "flora") else 80
    d["animation"] = {"frames": frames, "frame_ms": 220 if frames > 1 else 200}
    return d


def _fit(template: list[str], W: int, H: int) -> list[int]:
    tw, th = len(template[0]), len(template)
    return [max(1, W // 2 - tw), max(1, (H - th) // 2)]


def fungus_type(f: dict) -> dict:
    cols = [colour(c) for c in (f.get("colors") or ["brown"])]
    cap = FUNGI.get(f.get("cap", "round"), FUNGI["round"])
    ramps = [{"name": "cap", "weight": 3, "colors": ramp(cols[0], 4, 0.3)}]
    if len(cols) > 1:
        ramps.append({"name": "cap_alt", "weight": 1, "colors": ramp(cols[1], 4, 0.3)})
    ramps.append({"name": "stem", "weight": 0, "colors": ramp(colour("cream") if len(cols) < 3 else cols[2], 3, 0.25)})
    if f.get("glows"):
        ramps[0]["colors"] = ramp(cols[0], 4, 0.22)[1:] + [ramp(cols[0], 5, 0.4)[-1]]
    stem = (f.get("cap") not in ("shelf", "coral", "cluster"))
    W = H = 16
    body_anchor = [1, 2]
    parts = [("stem", 100, [5, 2 + len(cap)], [".##", ".##", "1##", "2##"], "stem")] if stem else []
    parts.append(("spots", 55, [W // 2 - 3, 3], ["1.1", ".1."], "stem"))   # pale spots on the cap, some seeds
    d = mask_doc(f"boc.fungus.{f['id']}", "flora", (W, H), f["name"], "book-of-cities: fungi" + (f" ({f['biome']})" if f.get("biome") else ""),
                 bool(f.get("inferred_colors")), ramps, cap, body_anchor, parts)
    if f.get("glows"):
        d["glows"] = True
    if f.get("biome"):
        d["biome"] = f["biome"]
    return d


def fauna_type(f: dict, kind: str) -> dict:
    body_plan = "fish" if kind == "fish" else f.get("body", "other")
    W, H, k2 = SIZE_OF.get(f.get("size", "small"), SIZE_OF["small"])
    t = FAUNA.get(body_plan, FAUNA["other"])
    big = upscale(t, k2) if k2 != 2 else t
    if len(big[0]) <= W // 2 - 1 and len(big) <= H - 2:
        t = big
    else:
        k2 = 2
    cols = [colour(c) for c in (f.get("colors") or ["brown"])]
    ramps = [{"name": "coat", "weight": 3, "colors": ramp(cols[0], 4, 0.3)}]
    if len(cols) > 1:
        ramps.append({"name": "coat_alt", "weight": 1, "colors": ramp(cols[1], 4, 0.3)})
    parts = []
    for name, ch, a, pt, in [(p[0], p[1], p[2], p[3]) for p in FAUNA_PARTS.get(body_plan, [])]:
        if k2 != 2:
            pt = upscale(pt, k2)
            a = [a[0] * k2 // 2, a[1] * k2 // 2]
        anchor = _fit(t, W, H)
        a2 = [W // 2 - len(pt[0]), anchor[1] + a[1]]          # centred, so the mirror stays symmetric
        if a2[0] + 2 * len(pt[0]) <= W - 1 and a2[1] + len(pt) <= H - 1 and a2[0] >= 1:
            parts.append((name, ch, a2, pt, "coat_alt" if len(cols) > 1 else None))
    src = "book-of-cities: " + ("fish" if kind == "fish" else "fauna") + (f" ({f['biome']})" if f.get("biome") else "")
    d = mask_doc(f"boc.{kind}.{f['id']}", "creature.small" if W <= 16 else "creature", (W, H), f["name"], src, bool(f.get("inferred_colors")),
                 ramps, t, _fit(t, W, H), parts, eyes=0 if body_plan in ("insect",) else 2 if body_plan in ("quadruped", "bird", "amphibian", "other") else 1,
                 frames=3 if body_plan in ("slime", "fish") else 1)
    if f.get("biome"):
        d["biome"] = f["biome"]
    return d


def _crucible_index():
    m = load("crucible_materials.json")
    idx = {}
    for x in m["materials"]:
        idx.setdefault(x["name"].lower(), x)
        idx.setdefault(x["name"].lower().split(" (")[0], x)
    bridge = {r["boc_material"].lower(): r for r in m["boc_bridge_rows"]}
    return idx, bridge, m


CATEGORY_DENSITY = {"metal": 7800, "stone": 2600, "gem": 3500, "mineral": 2700, "glass": 2500, "organic": 1300, "bone": 1900, "salt": 2160, "clay": 1800}


def ore_type(o: dict, cidx, bridge) -> dict:
    name = o["name"]
    low = name.lower()
    shape = ("crystal" if any(k in low for k in ("crystal", "gem", "opal", "stone", "glass", "turquoise", "moonstone", "obsidian")) and "stone" not in ("limestone", "sandstone")
             else "round" if "pearl" in low else "chunk")
    if low in ("limestone", "sandstone", "flint", "clay", "plains clay", "peat", "salt", "sea salt", "coral stone", "pressure stone", "wither stone", "shadow stone"):
        shape = "chunk"
    col = colour(o.get("color") or "grey")
    real = (o.get("real_material") or "").lower()
    br = bridge.get(low) or bridge.get(low.replace(" ore", "") + " ore")
    mat = cidx.get(real) or cidx.get(real.replace(" ore", "")) if real else None
    grounding = "intentionally_ungrounded" if o.get("fantasy") else "grounded" if mat and mat.get("density_kg_m3") else "category_default"
    cat = ("metal" if any(k in low for k in ("ore", "iron", "metal", "gold", "silver", "mithril", "adamant", "steel")) else
           "gem" if shape == "crystal" else "organic" if any(k in low for k in ("pearl", "amber", "peat", "coral", "ivory")) else
           "salt" if "salt" in low else "clay" if "clay" in low else "stone")
    dens = mat.get("density_kg_m3") if mat and mat.get("density_kg_m3") and not o.get("fantasy") else None
    crucible = {"grounding": grounding, "density_kg_m3": dens if dens else CATEGORY_DENSITY[cat], "category": cat}
    if mat:
        crucible["crucible_ref"] = mat["id"]
        crucible["crucible_name"] = mat["name"]
        if mat.get("melting_point_K"):
            crucible["melting_point_K"] = mat["melting_point_K"]
    if br:
        crucible["boc_bridge_id"] = br["id"]
        crucible["boc_bridge_mode"] = br.get("grounding_mode") or ""
    crucible["chunk_grams"] = crucible["density_kg_m3"] // 2          # a 500 cm3 chunk
    crucible["note"] = {"grounded": "density from CRUCIBLE", "category_default": f"CRUCIBLE has no density here; a typical {cat} density is used",
                        "intentionally_ungrounded": "fantasy material: CRUCIBLE's rule is never to fill it from real data; the weight is authored"}[grounding]
    stone = ramp(colour("stone"), 4, 0.28)
    if shape == "chunk" and cat in ("metal",):
        ramps = [{"name": "stone", "weight": 1, "colors": stone}, {"name": "ore", "weight": 0, "colors": ramp(col, 4, 0.36)}]
        body, parts = ORE_CHUNK, [("vein", 100, [1, 6], ORE_VEIN, "ore")]
    elif shape == "chunk":
        ramps = [{"name": "rock", "weight": 1, "colors": ramp(col, 4, 0.3)}]
        body, parts = ORE_CHUNK, []
    else:
        ramps = [{"name": "gem", "weight": 1, "colors": ramp(col, 4, 0.4)}]
        body, parts = (ORE_CRYSTAL if shape == "crystal" else ORE_ROUND), []
    d = mask_doc(f"boc.ore.{o['id']}", "ore", (16, 16), name, "book-of-cities: ores" + (f" ({o['biome']})" if o.get("biome") else ""),
                 bool(o.get("inferred_colors")), ramps, body, _fit(body, 16, 16), parts)
    d["rarity"] = o.get("rarity", "common")
    d["fantasy"] = bool(o.get("fantasy"))
    if o.get("biome"):
        d["biome"] = o["biome"]
    d["crucible"] = crucible
    return d


RANK_COLOURS = {"common": "stone", "uncommon": "green", "greater": "blue", "rare": "blue", "master": "violet", "legendary": "gold",
                "s": "silver", "ss": "gold", "sss": "crimson", "wild": "moss", "standard": "bronze", "beyond_master": "amethyst",
                "improvised": "bark", "basic": "stone", "masterwork": "violet"}


def rank_type(r: dict) -> dict:
    key = r["id"].split("-", 1)[-1].replace("-rank", "")
    word = RANK_COLOURS.get(key, "slate")
    d = head_doc(f"boc.rank.{r['id'].replace('-', '_')}", "ui", "uikit", (12, 12), r["name"], "book-of-cities-compendium: ranks", True)
    d.update({"tile": 12, "border": 2 if (r["order"] if isinstance(r.get("order"), int) else 1) < 4 else 3, "corner": "round", "icons": 6, "texture": 8 + 2 * min(8, r["order"] if isinstance(r.get("order"), int) else 1),
              "palette": {"outline": "#14121a", "material": ramp(colour(word), 5, 0.36)}})
    d["rank_order"] = r["order"] if isinstance(r.get("order"), int) else 0
    return d


TRAIT_OVERLAYS = {  # trait id -> (label, species overrides, skin tint word or None)
    "axis-flame": ("Flame-touched", {"iris": ["red", "amber"], "accessories": [{"item": "tattoo", "chance": 70}]}, None),
    "axis-frost": ("Frost-touched", {"iris": ["ice"], "hair_color": ["white", "silver"]}, None),
    "axis-shadow": ("Shadow-touched", {"iris": ["violet"], "hair_color": ["black"]}, None),
    "axis-divine": ("Divine-touched", {"iris": ["gold"], "hair_color": ["white", "gold"]}, None),
    "axis-infernal": ("Infernal-touched", {"iris": ["red"], "accessories": [{"item": "tattoo", "chance": 90}]}, None),
    "axis-nature": ("Nature-bound", {"iris": ["green"], "hair_color": ["moss"]}, None),
    "axis-water": ("Water-bound", {"iris": ["ice", "blue"], "accessories": [{"item": "fins", "chance": 60}]}, None),
    "axis-fey": ("Fey-touched", {"iris": ["violet", "green"], "hair_color": ["silver", "moss"]}, None),
    "axis-celestial-lunar": ("Moon-touched", {"iris": ["silver"], "hair_color": ["silver", "white"]}, None),
    "axis-celestial-solar": ("Sun-touched", {"iris": ["gold", "amber"], "hair_color": ["gold", "blond"]}, None),
    "axis-necromantic": ("Grave-touched", {"iris": ["ice", "violet"]}, "ashen"),
    "axis-ferocity": ("Ferocious", {"iris": ["red"], "accessories": [{"item": "tusks", "chance": 60}]}, None),
    "cold-water-adaptation": ("Cold-water adapted", {"accessories": [{"item": "fins", "chance": 100}]}, None),
    "night-vision": ("Night-eyed", {"iris": ["gold", "ice"], "eye": [112, 126]}, None),
}


def trait_overlay(tid: str, traits: dict) -> dict:
    label, sp, tint = TRAIT_OVERLAYS[tid]
    t = traits.get(tid, {})
    d = {"schema": SCHEMA, "id": f"boc.trait.sub.{tid.replace('-', '_')}", "extends": "boc.goblin", "tag": "creature.humanoid.goblin", "license": LICENSE,
         "label": label, "provenance": {"source": "book-of-cities-compendium: traits", "trait": tid, "summary": t.get("summary", ""),
                                         "visual": "inferred: the Compendium describes mechanics, not looks"},
         "species": sp, "palette": {"hair": HAIR_EXTRA, "iris": IRIS_EXTRA}}
    if tint:
        d["palette"]["materials"] = {"skin": ramp(colour(tint), 5)}
    return d


AETHER_ROLES = {"aelren": "elder_scholar", "hessel": "arcanist", "tiwa": "teenager", "maerin-joren": "shaman", "tutelary-saint": "village_chief"}


def aether_pack(a: dict) -> tuple[dict, list[tuple[str, str]], str]:
    """The Aether Library pack: named souls as seeds (never an overwrite), and Brackrun-Hollow as a hamlet."""
    ents = []
    for e in a["entities"]:
        if not e["kind"].startswith("character") and "deity" not in e["kind"]:
            continue
        ents.append({"id": e["id"], "name": e["name"], "soul_name": e["name"], "role": f"boc.goblin.{AETHER_ROLES.get(e['id'], 'father')}",
                     "sub": "boc.race.sub.human", "kind": e["kind"], "summary": e.get("summary", "")})
    reg = {"schema": "pixelgoblin/souls@1", "id": "boc.aether.souls", "license": LICENSE,
           "rule": "supplement-but-never-overwrite: a PixelGoblin avatar is a new appearance offered for a soul; it never replaces an existing identity, and nothing is written into the Aether Library",
           "seed": "seed = seed_from_name('soul:' + soul_name); soul_name survives reincarnation, so the avatar does too",
           "source": "aether-library: GLOSSARY.md, canonical documents, db (read-only)", "entities": ents}
    city = {"schema": "pixelgoblin/city@1", "id": "boc.city.brackrun_hollow", "scene": "boc.scene.village", "clans": [],
            "census": {"gatherer": 3, "hunter": 2, "father": 2, "mother": 2, "trader": 1, "shaman": 1, "elder_scholar": 1, "craftswoman": 1},
            "children": {"child_boy": 1, "child_girl": 1}, "elders": {"elder": 1},
            "subspecies": {"boc.race.sub.human": 4, "boc.race.sub.halfling": 1, "common": 1}, "bands": {"far": 4, "mid": 3, "near": 1}}
    people = [part.strip().split(" of ")[0] for e in ents if e["kind"].startswith("character") for part in e["name"].split("/")]
    names = "\n".join(n for n in people if n) + "\n"
    return reg, [("brackrun_hollow.city.toml", toml(city, "Brackrun-Hollow, the Aether Library's hamlet, as a PixelGoblin city of mixed folk.\nNames: brackrun_hollow.names.txt (the named souls of the Aether Library)."))], names


def manifest(pid, label, source, files, types, inferred, extra=None, data_files=()) -> str:
    d = {"schema": PACK_SCHEMA, "id": f"boc.pack.{pid}", "label": label, "license": LICENSE, "built": FORGED, "builder": "tools/build_packs.py",
         "source": source, "counts": {"types": len(types), "inferred_colors": inferred}, "types": sorted(types)}
    if data_files:
        d["data"] = list(data_files)
    if extra:
        d.update(extra)
    return toml(d, f"{label}: a PixelGoblin resource pack. Generated by tools/build_packs.py; do not edit by hand.\nEach type file carries a [provenance] table naming its source.")


def build() -> dict[Path, str]:
    boc, comp, aeth = load("boc.json"), load("compendium.json"), load("aether.json")
    cidx, bridge, cm = _crucible_index()
    out: dict[Path, str] = {}

    def put(pack, name, doc, head):
        out[PACKS / pack / name] = toml(doc, head) if isinstance(doc, dict) else doc

    # races
    by_id = {r["id"]: r for r in boc["races"]}
    ids, inf = [], 0
    for r in boc["races"]:
        rid, doc = race_overlay(r, by_id)
        put("races", f"{rid}.toml", doc, f"{r['name']}: an overlay for any role, like a subspecies: typefile.compose(role, 'boc.race.sub.{rid}'), or --sub {rid.replace('_', '-')} ... use the full id.")
        ids.append(doc["id"]); inf += bool(r.get("inferred_colors"))
    out[PACKS / "races" / "pack.toml"] = manifest("races", "Folk of the Book of Cities", {"skill": "book-of-cities", "files": boc["source_files"]}, [], ids, inf,
                                                  {"usage": "overlays: combine any race with any job (pixelgoblin view boc.goblin.blacksmith --sub boc.race.sub.dwarf)",
                                                   "note": "stature is relative to goblin height and capped by the canvas: humans draw about 1.2x a goblin (the source's real ratio is about 1.4x)"})
    # biomes
    ids, inf = [], 0
    for b in boc["biomes"]:
        for name, doc in biome_types(b):
            put("biomes", f"{name}.toml", doc, f"{b['name']}: {b.get('summary', '')}")
            ids.append(doc["id"])
        inf += bool(b.get("inferred_colors"))
    residents = {}
    for sec, pre in (("flora", "boc.flora."), ("fungi", "boc.fungus."), ("fauna", "boc.fauna."), ("fish", "boc.fish."), ("ores", "boc.ore.")):
        for e in boc[sec]:
            if e.get("biome"):
                residents.setdefault(e["biome"], []).append(pre + e["id"])
    out[PACKS / "biomes" / "pack.toml"] = manifest("biomes", "Biomes of the Book of Cities", {"skill": "book-of-cities", "files": boc["source_files"]}, [], ids, inf,
                                                   {"residents": {k: sorted(v) for k, v in sorted(residents.items())}})
    # flora + fungi
    ids, inf = [], 0
    for f in boc["flora"]:
        d = flora_type(f); put("flora", f"{f['id']}.toml", d, f"{f['name']}: {f.get('notes', '')}".strip()); ids.append(d["id"]); inf += bool(f.get("inferred_colors"))
    for f in boc["fungi"]:
        d = fungus_type(f); put("flora", f"fungus.{f['id']}.toml", d, f"{f['name']}{' (glows)' if f.get('glows') else ''}"); ids.append(d["id"]); inf += bool(f.get("inferred_colors"))
    out[PACKS / "flora" / "pack.toml"] = manifest("flora", "Flora and fungi of the Book of Cities", {"skill": "book-of-cities", "files": boc["source_files"]}, [], ids, inf)
    # fauna + fish
    ids, inf = [], 0
    for f in boc["fauna"]:
        d = fauna_type(f, "fauna"); put("fauna", f"{f['id']}.toml", d, f"{f['name']}: {f.get('notes', '')}".strip()); ids.append(d["id"]); inf += bool(f.get("inferred_colors"))
    for f in boc["fish"]:
        d = fauna_type(f, "fish"); put("fauna", f"fish.{f['id']}.toml", d, f"{f['name']} ({f.get('water', 'water')})"); ids.append(d["id"]); inf += bool(f.get("inferred_colors"))
    out[PACKS / "fauna" / "pack.toml"] = manifest("fauna", "Fauna and fish of the Book of Cities", {"skill": "book-of-cities", "files": boc["source_files"]}, [], ids, inf)
    # ores, grounded in CRUCIBLE
    ids, inf, g = [], 0, {"grounded": 0, "category_default": 0, "intentionally_ungrounded": 0}
    for o in boc["ores"]:
        d = ore_type(o, cidx, bridge); put("ores", f"{o['id']}.toml", d, f"{o['name']} ({o.get('rarity', 'common')}{', fantasy' if o.get('fantasy') else ''})")
        ids.append(d["id"]); inf += bool(o.get("inferred_colors")); g[d["crucible"]["grounding"]] += 1
    out[PACKS / "ores" / "pack.toml"] = manifest("ores", "Ores, stones and gems, grounded in CRUCIBLE",
                                                 {"skill": "book-of-cities + crucible", "files": boc["source_files"] + ["crucible/build/db/crucible.db (materials, elements, compounds, boc_bridge)"]},
                                                 [], ids, inf, {"grounding": g})
    # data catalogs (stations, districts) travel as data
    cat = {"schema": "pixelgoblin/catalog@1", "id": "boc.catalog.world", "license": LICENSE, "source": "book-of-cities",
           "stations": boc["stations"], "districts": boc["districts_or_buildings"]}
    out[PACKS / "world" / "world.catalog.json"] = json.dumps(cat, indent=1, ensure_ascii=False) + "\n"
    out[PACKS / "world" / "pack.toml"] = manifest("world", "Stations and districts of the Book of Cities (data)", {"skill": "book-of-cities", "files": boc["source_files"]},
                                                  [], [], 0, {"note": "data only: the sandbox uses the stations for crafting tiers"}, ["world.catalog.json"])
    # compendium: ranks as UI kits, traits as overlays, the rest as data
    ids = []
    for r in comp["ranks"]:
        d = rank_type(r); put("compendium", f"rank.{r['id']}.toml", d, f"{r['name']}: {r.get('summary', '')}"[:200]); ids.append(d["id"])
    traits = {t["id"]: t for t in comp["traits"]}
    for tid in TRAIT_OVERLAYS:
        d = trait_overlay(tid, traits); put("compendium", f"trait.{tid}.toml", d, f"{d['label']}: a trait overlay. Stack it after a race: --sub boc.race.sub.elf,{d['id']}"); ids.append(d["id"])
    out[PACKS / "compendium" / "compendium.catalog.json"] = json.dumps({"schema": "pixelgoblin/catalog@1", "id": "boc.catalog.compendium", "license": LICENSE,
                                                                         **{k: comp[k] for k in comp if k != "source_files"}}, indent=1, ensure_ascii=False) + "\n"
    out[PACKS / "compendium" / "pack.toml"] = manifest("compendium", "Book of Cities Compendium: ranks, trait overlays, catalog",
                                                       {"skill": "book-of-cities-compendium-builder", "files": comp["source_files"]}, [], ids, len(ids),
                                                       {"note": "the Compendium describes mechanics, not looks: every visual here is inferred and flagged"}, ["compendium.catalog.json"])
    # aether library
    reg, cities, names = aether_pack(aeth)
    out[PACKS / "aether" / "souls.toml"] = toml(reg, "The Aether Library's named souls, as PixelGoblin avatar seeds (pixelgoblin avatar <name>).")
    for n, text in cities:
        out[PACKS / "aether" / n] = text
    out[PACKS / "aether" / "brackrun_hollow.names.txt"] = names
    out[PACKS / "aether" / "aether.catalog.json"] = json.dumps({"schema": "pixelgoblin/catalog@1", "id": "boc.catalog.aether", "license": LICENSE,
                                                              **{k: aeth[k] for k in aeth if k != "source_files"}}, indent=1, ensure_ascii=False) + "\n"
    out[PACKS / "aether" / "pack.toml"] = manifest("aether", "Aether Library: souls, Brackrun-Hollow, catalog", {"skill": "aether-library-pseudoskill", "files": aeth["source_files"]},
                                                   [], [], 0, {"rule": reg["rule"]}, ["souls.toml", "brackrun_hollow.city.toml", "brackrun_hollow.names.txt", "aether.catalog.json"])
    if UNRESOLVED:
        print("colour words not resolved (hashed to a muted colour):", sorted(set(UNRESOLVED)), file=sys.stderr)
    return out


def main() -> int:
    files = build()
    if "--check" in sys.argv:
        stale = [str(p.relative_to(ROOT)) for p, t in files.items() if not p.exists() or p.read_text() != t]
        extra = [str(p.relative_to(ROOT)) for p in PACKS.rglob("*") if p.is_file() and "sources" not in p.parts and p not in files]
        for s in stale + extra:
            print("stale:", s)
        return 1 if stale or extra else 0
    for p in PACKS.rglob("*"):
        if p.is_file() and "sources" not in p.parts and p not in files:
            p.unlink()
    for p, t in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t)
    print(f"{len(files)} pack files in {PACKS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
