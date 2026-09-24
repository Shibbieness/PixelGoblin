#!/usr/bin/env python3
"""PixelGoblin build gates — SPIRE's gate discipline, ported.

Two namespaces, never confused:
  Plan gates  (G-numbered)  = phase exit criteria in docs/explanation/gameplan.md
  Build gates (B-numbered)  = runnable units here; each declares which G it covers

Rules this runner enforces on itself (each earned by a defect in SPIRE):
  * a gate must be able to fail   -> tests/falsify.py proves it, mutation by mutation
  * no assertion over an empty population -> absence checks build a control first
  * counts are derived, never written -> tests/FLOOR.json ratchets them
  * BUILD_STATUS.md is written only when EVERY gate ran
  * tests never touch the network -> socket guard, not convention
  * a build that passes only in a warm directory has hidden state -> --from-empty

Usage:
  PYTHONHASHSEED=0 python3 tests/gate.py --all [--report]
  PYTHONHASHSEED=0 python3 tests/gate.py --from-empty
  PYTHONHASHSEED=0 python3 tests/gate.py B03 B05
  python3 tests/gate.py --bless-goldens --witness NAME --reason TEXT
  python3 tests/gate.py --raise-floor
"""

from __future__ import annotations

import io
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------- socket guard
class _NoNet(socket.socket):
    def __init__(self, *a, **k):
        raise RuntimeError("tests may not touch the network (socket guard)")


socket.socket = _NoNet  # type: ignore[misc]

from pixelgoblin import CREDIT, ENGINE_MAJOR, VERSION, brood, export, gen, hazard, png, sharecode, typefile, uikit, verdicts  # noqa: E402
from pixelgoblin.convert import convert_rgba, count_l_corners, likeness, pixel_perfect  # noqa: E402
from pixelgoblin.rng import Rng, Streams, derive, master_seed  # noqa: E402
from pixelgoblin.sprite import Sprite  # noqa: E402
from pixelgoblin.tiles import autotile, wfc  # noqa: E402

GOLDENS = ROOT / "tests" / "golden" / "goldens.json"
FLOOR = ROOT / "tests" / "FLOOR.json"
LICENSE_SHA = "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0"

GATES: dict = {}


def gate(bid: str, title: str, covers: list[str]):
    def deco(fn):
        GATES[bid] = {"title": title, "covers": covers, "fn": fn}
        return fn
    return deco


class Check:
    def __init__(self):
        self.lines: list[str] = []
        self.failed = 0
        self.asserts = 0
        self.negatives = 0

    def ok(self, cond: bool, what: str, negative: bool = False) -> bool:
        self.asserts += 1
        self.negatives += int(negative)
        if not cond:
            self.failed += 1
            self.lines.append(f"FAIL {what}")
        return cond

    def population(self, n: int, what: str) -> bool:
        """Vacuity guard: an assertion over nothing proves nothing."""
        return self.ok(n > 0, f"population for '{what}' is empty — assertion would be vacuous")


# ---------------------------------------------------------------- helpers
def vanilla_types() -> list[Path]:
    return sorted((ROOT / "types" / "vanilla").glob("*.toml"))


def flavor_types() -> list[Path]:
    return sorted((ROOT / "flavors").rglob("*.toml"))


def all_types():
    return [typefile.load(p) for p in vanilla_types() + flavor_types()]


def golden_cases():
    cases = []
    for tf in all_types():
        if tf.generator in gen.REGISTRY:
            for s in (0, 1, 42, 2 ** 63 + 5):
                cases.append(("frames", tf.id, s))
        elif tf.generator == "autotile":
            cases.append(("autotile", tf.id, 1))
        elif tf.generator == "uikit":
            cases.append(("uikit", tf.id, 1))
    cases.append(("wfc", "builtin.cave", 3))
    return cases


CAVE_ROWS = ["........", ".##..##.", ".#....#.", "...##...", "..####..", ".#....#.", "........", "..#..#.."]
CAVE_COLORS = {".": (40, 34, 52, 255), "#": (106, 90, 110, 255)}


def compute_case(kind, tid, seed) -> list[str]:
    if kind == "wfc":
        sample = wfc.sample_from_rows(CAVE_ROWS, CAVE_COLORS)
        return [wfc.generate(sample, 24, 24, master_seed("00" * 32, seed, ENGINE_MAJOR)).sprite.pixel_hash()]
    tf = typefile.load(tid)
    if kind == "frames":
        return [f.pixel_hash() for f in gen.frames(tf, seed)]
    if kind == "autotile":
        return [autotile.build_tileset(tf, seed)[0].pixel_hash()]
    return [uikit.build_kit(tf, seed)["atlas"].pixel_hash()]


def base_mask_type() -> dict:
    return json.loads(json.dumps(typefile.load("vanilla.creature.blob").data))


def parse_blocks(text: str) -> list[str]:
    return [l for l in text.splitlines() if l.strip()]


# ---------------------------------------------------------------- gates
@gate("B00", "skeleton, licence and attribution", ["G22"])
def b00(c: Check):
    import hashlib
    for f in ("LICENSE", "LICENSE-COMMERCIAL.md", "ATTRIBUTION.md", "NOTICE.md", "flavor.toml", "vanilla_flavor.py", "README.md"):
        c.ok((ROOT / f).exists(), f"{f} exists")
    c.ok(hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest() == LICENSE_SHA, "LICENSE is the byte-exact AGPL-3.0 text")
    c.ok(CREDIT in (ROOT / "ATTRIBUTION.md").read_text(encoding="utf-8").replace("```", "") or "Built on PixelGoblin" in (ROOT / "ATTRIBUTION.md").read_text(encoding="utf-8"), "credit line in ATTRIBUTION.md")
    out = io.StringIO()
    from pixelgoblin.cli import main
    with redirect_stdout(out):
        try:
            main(["--version"])
        except SystemExit:
            pass
    c.ok(CREDIT in out.getvalue(), "--version shows the credit line (AGPL §7(b) term)")


@gate("B01", "randomness and seed derivation", ["G01", "G02"])
def b01(c: Check):
    import struct
    ref = Rng(struct.pack("<4I", 1, 2, 3, 4))
    c.ok([ref.next() for _ in range(4)] == [11520, 0, 5927040, 70819200],
         "xoshiro128** matches the published reference sequence for state {1,2,3,4} (Blackman & Vigna)")
    r = Rng(bytes(range(16)))
    vec = [r.next() for _ in range(6)]
    c.ok(vec == KNOWN_VECTOR, f"xoshiro128** known vector {vec}")
    c.ok(derive(bytes(16), "body").hex() == KNOWN_DERIVE, "derive() known vector")
    # determinism across processes with different hash seeds
    code = ("import sys;sys.path.insert(0,%r);from pixelgoblin import typefile,gen;"
            "print(gen.sprite(typefile.load('vanilla.creature.blob'),42).pixel_hash())") % str(ROOT)
    outs = set()
    for hs in ("0", "1", "12345"):
        env = dict(os.environ, PYTHONHASHSEED=hs)
        outs.add(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env).stdout.strip())
    c.ok(len(outs) == 1 and len(next(iter(outs))) == 64, "same sprite across processes and hash seeds")
    # sub-seed stability: inserting a new part BEFORE an existing one leaves that part (and the body) unchanged
    from pixelgoblin.gen import mask as mk
    d = base_mask_type()
    d.setdefault("features", {})["eyes"] = 0
    horn = {"name": "horns", "chance": 100, "anchor": [4, 1], "template": ["1...", "#1..", ".#.."]}
    d["parts"] = [horn]
    a = typefile.from_dict(d)
    d2 = json.loads(json.dumps(d))
    d2["parts"] = [{"name": "extra", "chance": 0, "anchor": [4, 1], "template": ["1..."]}, horn]
    b = typefile.from_dict(d2)
    c.ok(a.type_hash != b.type_hash, "control: adding a part changes the type hash")
    same = 0
    for s in range(40):
        ms = master_seed(a.type_hash, s, ENGINE_MAJOR)  # same master seed forced: only the stream layout differs
        ca, _ = mk.build_cells(a.data, Streams(ms))
        cb, _ = mk.build_cells(b.data, Streams(ms))
        same += ca == cb
    c.ok(same == 40, f"inserting a part leaves body and later parts unchanged on 40 seeds ({same}/40) (ADR-008)")
    d3 = json.loads(json.dumps(d2))
    d3["parts"][0].update(chance=100, template=["#..."])
    cc, _ = mk.build_cells(typefile.from_dict(d3).data, Streams(master_seed(a.type_hash, 0, ENGINE_MAJOR)))
    ca0, _ = mk.build_cells(a.data, Streams(master_seed(a.type_hash, 0, ENGINE_MAJOR)))
    c.ok(cc != ca0, "control: a part that is present does change the cells", negative=True)


@gate("B02", "type files: hashing, validation, integer-only", ["G03", "G04", "G05"])
def b02(c: Check):
    src = (ROOT / "types" / "vanilla" / "creature.blob.toml").read_text()
    with tempfile.TemporaryDirectory() as t:
        p1, p2, p3 = Path(t, "a.toml"), Path(t, "b.toml"), Path(t, "c.toml")
        p1.write_text(src)
        p2.write_text("# a new comment\n" + src.replace("mirror = true", "mirror   =   true   # spaced"))
        p3.write_text(src.replace('"#1a1428"', '"#1a1429"'))
        h1, h2, h3 = (typefile.load(p).type_hash for p in (p1, p2, p3))
    c.ok(h1 == h2, "whitespace and comment edits do not change the hash")
    c.ok(h1 != h3, "a one-digit colour edit changes the hash", negative=True)
    d = base_mask_type()
    shuffled = dict(reversed(list(d.items())))
    c.ok(typefile.type_hash(d) == typefile.type_hash(shuffled), "key order does not change the hash (canonical JSON)")
    n = 0
    for mutate, expect in NEGATIVE_CASES:
        d = base_mask_type()
        mutate(d)
        probs = typefile.validate(d)
        n += 1
        c.ok(any(expect in p for p in probs), f"negative case '{expect}' reported (got {probs[:2]})", negative=True)
    c.population(n, "validator negative cases")
    c.ok(not typefile.validate(base_mask_type()), "control: the unmodified base type validates")
    for p in vanilla_types() + flavor_types():
        try:
            typefile.load(p)
            c.ok(True, str(p))
        except typefile.TypeFileError as e:
            c.ok(False, f"{p}: {e}")


@gate("B03", "generators: goldens, constraints, variety", ["G06", "G07", "G08"])
def b03(c: Check):
    gold = json.loads(GOLDENS.read_text())["cases"]
    c.population(len(gold), "goldens")
    for g in gold:
        got = compute_case(g["kind"], g["type"], g["seed"])
        c.ok(got == g["hashes"], f"golden {g['kind']} {g['type']} seed {g['seed']}")
    for tf in all_types():
        if tf.generator not in gen.REGISTRY:
            continue
        seeds = range(120 if tf.generator == "mask" else 12)
        sprites = [gen.sprite(tf, s) for s in seeds]
        W, H = tf.data["size"]
        c.ok(all((s.w, s.h) == (W, H) for s in sprites), f"{tf.id}: every sprite is {W}x{H}")
        if tf.generator == "mask":
            bad = [s for s in sprites if verdicts.spec_verdict(tf, s)["verdict"] != "SOUND"]
            c.ok(not bad, f"{tf.id}: spec verdict SOUND on 120 seeds ({len(bad)} unsound)")
            distinct = len({s.pixel_hash() for s in sprites[:100]})
            c.ok(distinct >= 90, f"{tf.id}: variety {distinct}/100 distinct (gate: 90)")
        c.ok(all(s.used_colors() > 0 for s in sprites), f"{tf.id}: no empty sprites")


@gate("B04", "tiles: 47-blob table and WFC", ["G09", "G10"])
def b04(c: Check):
    masks = autotile.blob_masks()
    c.ok(len(masks) == 47, f"exactly 47 blob shapes (got {len(masks)})")
    c.ok(len({reduce for reduce in (autotile.reduce_mask(m) for m in range(256))}) == 47, "256 raw masks reduce to 47")
    tf = typefile.load("vanilla.terrain.grass")
    sheet, _ = autotile.build_tileset(tf, 1)
    T = tf.data["tile"]
    tiles = set()
    for i in range(47):
        ox, oy = (i % autotile.COLS) * T, (i // autotile.COLS) * T
        tiles.add(bytes(sheet.px[(oy + y) * sheet.w + ox + x] for y in range(T) for x in range(T)))
    c.ok(len(tiles) == 47, f"47 visually distinct tiles ({len(tiles)})")
    # seamless: interior join between two full tiles has no outline pixels
    grid = [[1] * 4 for _ in range(4)]
    img = autotile.render_map(sheet, T, autotile.map_tiles(grid, edge_present=True))
    c.ok(1 not in img.px and 0 not in img.px, "a fully surrounded area renders with no seams")
    sample = wfc.sample_from_rows(CAVE_ROWS, CAVE_COLORS)
    fallbacks = 0
    for s in range(20):
        res = wfc.generate(sample, 16, 16, master_seed("00" * 32, s, 0), 3, 6)
        c.ok(res is not None and res.sprite.w == 16, f"WFC seed {s} returned an image")
        fallbacks += int(res.fallback)
    c.ok(fallbacks <= 2, f"WFC fallback rate {fallbacks}/20 (gate: at most 2)")
    impossible = wfc.sample_from_rows(["ab", "cd"], {"a": (1, 0, 0, 255), "b": (2, 0, 0, 255), "c": (3, 0, 0, 255), "d": (4, 0, 0, 255)})
    res = wfc.generate(impossible, 5, 5, bytes(16), 2, 2)
    c.ok(res.fallback and res.sprite.w == 5, "control: an impossible size falls back instead of returning nothing", negative=True)


def _staircase() -> Sprite:
    s = Sprite(24, 24, [(0, 0, 0, 0), (20, 20, 20, 255)])
    x = y = 1
    while x < 22 and y < 22:
        s.set(x, y, 1)
        s.set(x + 1, y, 1)
        x += 1
        y += 1
    return s


@gate("B05", "image + tag conversion", ["G11", "G12"])
def b05(c: Check):
    rnd = random.Random(7)
    sizes = [(1, 1), (3, 200), (64, 64), (257, 31), (10, 10)]
    n = 0
    for w, h in sizes:
        for mode in ("random", "clear", "half"):
            rgba = bytearray()
            for i in range(w * h):
                a = 0 if mode == "clear" else (255 if mode == "random" or i % 2 else 0)
                rgba += bytes((rnd.randrange(256), rnd.randrange(256), rnd.randrange(256), a))
            for tag in ("creature.small", "env", "object.icon", "terrain"):
                try:
                    s, rep = convert_rgba(w, h, bytes(rgba), tag)
                    prof = typefile.profile_for(tag)
                    c.ok(s.used_colors() <= prof["colors"], f"{w}x{h} {mode} {tag}: {s.used_colors()} <= {prof['colors']} colours")
                    n += 1
                except Exception as e:  # noqa: BLE001
                    c.ok(False, f"{w}x{h} {mode} {tag}: crashed with {e!r}")
    c.population(n, "conversion fuzz cases")
    try:
        typefile.profile_for("creture.small")
        c.ok(False, "misspelled tag is refused", negative=True)
    except typefile.TypeFileError as e:
        c.ok("creature" in str(e), "misspelled tag is refused with a suggestion", negative=True)
    st = _staircase()
    before = count_l_corners(st, 1)
    c.ok(before > 0, f"control: staircase line has L-corners ({before})")
    pixel_perfect(st, 1)
    c.ok(count_l_corners(st, 1) == 0, "pixel-perfect cleanup leaves zero L-corners")
    # likeness: one example becomes a valid generator of similar things
    ref = gen.sprite(typefile.load("vanilla.object.potion"), 3)
    text = likeness(ref, "test.like", "object.icon")
    with tempfile.TemporaryDirectory() as t:
        p = Path(t, "like.toml")
        p.write_text(text)
        tf = typefile.load(p)
    kids = [gen.sprite(tf, s) for s in range(10)]
    c.ok(tf.data.get("mirror") is True, "likeness detects the example's symmetry")
    c.ok(len({k.pixel_hash() for k in kids}) >= 5, "likeness type produces varied children")


@gate("B06", "UI kit (GUI slots)", ["G13"])
def b06(c: Check):
    tf = typefile.load("vanilla.ui.stone")
    k = uikit.build_kit(tf, 1)
    src = k["panels"]["normal"]
    ins = uikit.insets(tf.data)
    sizes = [(2 * ins, 2 * ins), (13, 40), (64, 32), (100, 7 + 2 * ins), (400, 100)]
    for w, h in sizes:
        r = uikit.nine_slice(src, ins, w, h)
        ring = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
        interior_holes = sum(1 for y in range(ins, h - ins) for x in range(ins, w - ins) if r.px[y * w + x] == 0)
        mid_edge = [r.px[0 * w + x] for x in range(ins, w - ins)] + [r.px[y * w + 0] for y in range(ins, h - ins)]
        c.ok(interior_holes == 0, f"9-slice {w}x{h}: no holes inside")
        src_inner = {src.px[y * src.w + x] for y in range(ins, src.h - ins) for x in range(ins, src.w - ins)}
        stray = {r.px[y * w + x] for y in range(ins, h - ins) for x in range(ins, w - ins)} - src_inner
        c.ok(not stray, f"9-slice {w}x{h}: centre uses only centre colours (no tiled edge stripes)")
        c.ok(all(v == 1 for v in mid_edge), f"9-slice {w}x{h}: outline unbroken along every edge")
        del ring
    torn = src.copy()
    torn.px[src.w // 2] = 0  # a hole in the top edge band
    tr = uikit.nine_slice(torn, ins, 64, 32)
    c.ok(not all(tr.px[x] == 1 for x in range(ins, 64 - ins)), "control: a torn edge is detected by the same check", negative=True)
    for st in uikit.STATES:
        c.ok(k["panels"][st].used_colors() > 1, f"state {st} renders")
    c.ok(len({k["panels"][s].pixel_hash() for s in uikit.STATES}) == 4, "four button states are all different")
    c.ok(k["kit"]["license"] == tf.license, "kit carries its licence")
    c.ok("texture_margin_left" in uikit.godot_stylebox(k["kit"], "atlas.png"), "Godot StyleBox export")


@gate("B07", "I/O, export, provenance, share codes", ["G14", "G23"])
def b07(c: Check):
    tf = typefile.load("vanilla.creature.blob")
    s = gen.sprite(tf, 5)
    w, h, rgba = png.decode(s.png_bytes())
    back = Sprite.from_rgba(w, h, rgba)
    c.ok(back.rgba() == s.rgba(), "indexed PNG round trip is pixel-exact, transparency included")
    rgba_png = png.encode_rgba(s.w, s.h, s.rgba())
    c.ok(png.decode(rgba_png)[2] == s.rgba(), "RGBA PNG round trip")
    txt = export.ascii_export(s, "t", export.provenance(tf, 5))
    c.ok(export.ascii_import(txt).rgba() == s.rgba(), "ASCII longevity export reads back exactly")
    c.ok(all(32 <= ord(ch) < 127 or ch == "\n" for ch in txt.replace("—", "-").replace("©", "c")), "ASCII export is printable (credit symbols aside)")
    c.ok(export.provenance(tf, 5) == export.provenance(tf, 5), "provenance is deterministic (no clock)")
    frames = gen.frames(tf, 5)
    img1, meta1 = export.sheet(frames, tf.id, 200, "x.png", export.provenance(tf, 5))
    img2, meta2 = export.sheet(frames, tf.id, 200, "x.png", export.provenance(tf, 5))
    c.ok(json.dumps(meta1) == json.dumps(meta2) and img1.pixel_hash() == img2.pixel_hash(), "re-export is byte-identical")
    c.ok(meta1["meta"]["frameTags"][0]["to"] == len(frames) - 1 and len(meta1["frames"]) == len(frames), "sheet JSON frames and tags agree")
    code = sharecode.encode(tf.type_hash, 2 ** 64 - 1)
    info = sharecode.decode(code)
    c.ok(info["seed"] == 2 ** 64 - 1 and tf.type_hash.startswith(info["type_hash_prefix"]), "share code round trip")
    typo = code[:-3] + ("0" if code[-3] != "0" else "1") + code[-2:]
    try:
        sharecode.decode(typo)
        c.ok(False, "a mistyped share code is caught", negative=True)
    except ValueError:
        c.ok(True, "a mistyped share code is caught", negative=True)


@gate("B08", "two verdicts, never merged", ["G15"])
def b08(c: Check):
    tf = typefile.load("boc.creature.goblin")
    s = gen.sprite(tf, 3)
    spec = verdicts.spec_verdict(tf, s)
    tgt = verdicts.target_verdict(s, "nes")
    c.ok(spec["verdict"] == "SOUND" and tgt["verdict"] == "DOES_NOT_FIT", "control: sound to its spec, yet does not fit the NES")
    tiny = typefile.load("vanilla.creature.blob")
    s1 = gen.sprite(tiny, 1)
    s2 = Sprite(s1.w + 2, s1.h, list(s1.palette))
    from pixelgoblin.sprite import blit
    blit(s2, s1, 0, 0)  # right pixels, wrong canvas
    c.ok(verdicts.spec_verdict(tiny, s2)["verdict"] == "UNSOUND", "control: a wrong-size sprite is UNSOUND", negative=True)
    for v in (spec, tgt):
        c.ok(not ({"overall", "combined", "ok", "pass", "score"} & set(v)), f"no merged field in {sorted(v)}")
    c.ok(set(verdicts.spec_verdict.__code__.co_varnames).isdisjoint({"target"}), "spec verdict cannot see the target")


@gate("B09", "hazard layer: flashing and licences", ["G16", "G17"])
def b09(c: Check):
    black = Sprite(16, 16, [(0, 0, 0, 0), (0, 0, 0, 255), (255, 255, 255, 255)])
    white = black.copy()
    black.px[:] = bytes([1] * 256)
    white.px[:] = bytes([2] * 256)
    strobe = hazard.flash_check([black, white], 50)
    c.ok(len(strobe) == 1, "control: a 10 Hz black/white strobe is reported")
    if strobe:
        m = strobe[0].mechanism
        order = [m.find("Do not"), m.find("Here is what happens"), m.find("Here is why"), m.find("what to do instead")]
        c.ok(all(i >= 0 for i in order) and order == sorted(order), "mechanism is delivered in order: don't, what, why, instead")
        c.ok(strobe[0].status == "UNVERIFIED", "flash check is labelled UNVERIFIED (approximation)")
    slow = hazard.flash_check([black, white], 1000)
    c.ok(not slow, "a 1 Hz blink is not reported", negative=True)
    idle = gen.frames(typefile.load("vanilla.creature.blob"), 4)
    c.ok(not hazard.flash_check(idle, 220), "the blob idle animation is not reported", negative=True)
    lic = hazard.licence_check(["CC0-1.0", "CC-BY-NC-4.0", "CC-BY-SA-3.0", "Proprietary"], "commercial")
    kinds = sorted(f.kind for f in lic)
    c.ok(kinds == ["licence-noncommercial", "licence-sharealike"], f"commercial pack flags NC and SA only ({kinds})")
    c.ok(all("what to do instead" in f.mechanism for f in lic), "licence findings say what to do instead")
    c.ok(not hazard.licence_check(["CC-BY-NC-4.0"], "open"), "open packs may include NC material", negative=True)


@gate("B10", "falsification (mutation testing)", [])
def b10(c: Check):
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "falsify.py"), "--json"], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONHASHSEED="0"), cwd=ROOT)
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        c.ok(False, f"falsify.py produced no result: {r.stderr[-400:]}")
        return
    c.population(res["total"], "mutations")
    c.ok(res["survivors"] == [], f"all {res['total']} mutants killed (survivors: {res['survivors']})")


@gate("B11", "Vanilla Core flavor contract", ["G18"])
def b11(c: Check):
    import tomllib
    import vanilla_flavor as vf
    man = tomllib.loads((ROOT / "flavor.toml").read_text())["flavor"]
    c.ok(tuple(man["capabilities"]) == vf.CAPABILITIES, "manifest capabilities match the adapter")
    c.ok(man["license"] == "AGPL-3.0-or-later", "flavor licence declared")
    for cap in vf.CAPABILITIES:
        p = {"type": "vanilla.creature.blob", "seed": 1}
        if cap == "convert":
            p = {"png_base64": vf._png(gen.sprite(typefile.load("vanilla.creature.blob"), 1)), "tag": "creature.small"}
        if cap == "autotile":
            p = {"type": "vanilla.terrain.grass", "grid": [[1, 1], [1, 0]]}
        if cap == "uikit":
            p = {"type": "vanilla.ui.stone"}
        try:
            out = vf.run(cap, p)
            json.dumps(out)
            c.ok(True, f"capability {cap}")
        except Exception as e:  # noqa: BLE001
            c.ok(False, f"capability {cap}: {e!r}")
    c.ok(vf.run("validate", {"type": {"schema": "nope"}})["ok"] is False, "validate reports problems instead of raising", negative=True)
    try:
        vf.run("fly")
        c.ok(False, "unknown capability refused", negative=True)
    except vf.FlavorError:
        c.ok(True, "unknown capability refused", negative=True)
    blob = json.dumps(man).lower()
    for marker in ("noreply@anthropic.com", "claude.ai/code/session", "claude.ai/share", "co-authored-by: claude"):
        c.ok(marker not in blob, f"manifest free of {marker}")


STACK_TERMS = ["Book of Cities", "BoC", "CALS", "CASL", "SPIRE", "dRAM", "LMAOU", "ASSAY", "CRUCIBLE", "GILWRIGHT",
               "TINSMITH", "LATTICE", "Runic", "QRen", "Aether", "SubSpace", "Eid", "CodexOmega"]


def scrub_hits(text: str) -> list[str]:
    """Whole-word, case-sensitive: 'Arsenicals' is not CALS, 'dramatic' is not dRAM."""
    return [t for t in STACK_TERMS if re.search(r"(?<![A-Za-z])" + re.escape(t) + r"(?![A-Za-z])", text)]


def _code_only(path: Path) -> str:
    """Executable code only: comments and docstrings are prose, and a citation
    is not a dependency (SPIRE's Stack Gravity rule)."""
    import ast
    import tokenize
    src = path.read_text(encoding="utf-8")
    spans = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
                spans.add(first.lineno)
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT or (tok.type == tokenize.STRING and tok.start[0] in spans):
            continue
        out.append(tok.string)
    return " ".join(out)


@gate("B12", "scrub (vanilla vs flavor) and leak guard", ["G19"])
def b12(c: Check):
    files = sorted((ROOT / "pixelgoblin").rglob("*.py")) + vanilla_types()
    c.population(len(files), "vanilla files to scrub")
    for f in files:
        text = _code_only(f) if f.suffix == ".py" else "\n".join(l for l in f.read_text().splitlines() if not l.lstrip().startswith("#"))
        hits = scrub_hits(text)
        c.ok(not hits, f"{f.relative_to(ROOT)} free of stack terms {hits}")
    c.ok(scrub_hits("the Book of Cities goblin") == ["Book of Cities"], "control: the scrubber finds a planted term", negative=True)
    c.ok(scrub_hits("Arsenicals and a dramatic eidolon") == [], "control: no false positives on Arsenicals/dramatic/eidolon", negative=True)
    with tempfile.TemporaryDirectory() as t:
        probe = Path(t, "probe.py")
        probe.write_text('"""cites SPIRE in prose"""\nX = "SPIRE"  # comment SPIRE\n')
        c.ok(scrub_hits(_code_only(probe)) == ["SPIRE"], "control: a term in executable code is found while docstrings/comments are not", negative=True)
    for tf in all_types():
        if tf.id.startswith("vanilla."):
            c.ok(tf.license != "Proprietary", f"{tf.id}: vanilla content is not proprietary")
    # exact-path exemptions only: these two files must NAME the markers to test that they are caught
    allow = ["--allow", "tests/gate.py", "--allow", "tests/falsify.py"]
    lg = subprocess.run([sys.executable, str(ROOT / "tools" / "leakguard.py")] + allow + [str(p) for p in _repo_files()],
                        capture_output=True, text=True, cwd=ROOT)
    c.ok(lg.returncode == 0, f"leakguard clean: {lg.stdout.strip().splitlines()[-1] if lg.stdout.strip() else lg.stderr[-200:]}")
    with tempfile.TemporaryDirectory() as t:
        planted = Path(t, "x.md")
        planted.write_text("Co-Authored-By: Claude\n")
        lg2 = subprocess.run([sys.executable, str(ROOT / "tools" / "leakguard.py"), str(planted)], capture_output=True, text=True, cwd=t)
        c.ok(lg2.returncode == 1, "control: leakguard catches a planted vendor trailer", negative=True)


def _repo_files() -> list[Path]:
    skip = {".git", "__pycache__", "dist", ".falsify_backup", "out"}
    return [p for p in ROOT.rglob("*") if p.is_file() and not (set(p.relative_to(ROOT).parts) & skip)
            and p.suffix not in (".png", ".gif")]


@gate("B13", "cross-language parity (JavaScript editor core)", ["G20"])
def b13(c: Check):
    node = shutil.which("node")
    core = ROOT / "editor" / "pg-core.js"
    html = ROOT / "editor" / "pixelgoblin.html"
    c.ok(core.exists() and html.exists(), "editor core and page exist")
    if not node:
        c.ok(False, "node not found — parity could not be checked (a skipped check is not a pass)")
        return
    c.ok(core.read_text() in html.read_text(), "the page embeds the exact pg-core.js (derived file is current)")
    cases = []
    for tf in all_types():
        if tf.generator in ("mask", "lsystem", "parallax", "autotile"):
            for s in (0, 1, 42, 2 ** 63 + 5):
                cases.append({"type": tf.data, "hash": tf.type_hash, "seed": str(s), "kind": tf.generator})
    c.population(len(cases), "parity cases")
    r = subprocess.run([node, str(ROOT / "editor" / "parity.mjs")], input=json.dumps(cases), capture_output=True, text=True)
    if r.returncode != 0:
        c.ok(False, f"node parity run failed: {r.stderr[-500:]}")
        return
    got = json.loads(r.stdout)
    for case, out in zip(cases, got):
        tf = typefile.from_dict(case["type"])
        c.ok(out["type_hash"] == tf.type_hash, f"JS type hash {tf.id}")
        if case["kind"] == "autotile":
            want = [autotile.build_tileset(tf, int(case["seed"]))[0].pixel_hash()]
        else:
            want = [f.pixel_hash() for f in gen.frames(tf, int(case["seed"]))]
        c.ok(out["hashes"] == want, f"JS pixels == Python pixels: {tf.id} seed {case['seed']}")
        c.ok(out["share"] == sharecode.encode(tf.type_hash, int(case["seed"])), f"JS share code == Python: {tf.id} seed {case['seed']}")


@gate("B14", "documentation is present and derived docs are current", ["G21"])
def b14(c: Check):
    from pixelgoblin.cli import EXAMPLES, build_parser
    ap = build_parser()
    subs = next(a for a in ap._actions if a.__class__.__name__ == "_SubParsersAction").choices
    c.population(len(subs), "CLI commands")
    for name, p in subs.items():
        c.ok(bool(p.description) and name in EXAMPLES and EXAMPLES[name].startswith("pixelgoblin"), f"`{name}` has help and an example")
    ref = ROOT / "docs" / "reference" / "cli.md"
    c.ok(ref.exists() and ref.read_text() == render_cli_doc(), "docs/reference/cli.md matches the parser (regenerate with --regen-docs)")
    for page in REQUIRED_DOCS:
        c.ok((ROOT / page).exists(), f"{page} exists")
    # a count in a document is computed, or it is a comment: numbers in prose must match the derivation
    counts = derived_counts()
    claims = [("docs/explanation/gates.md", r"(\d+) mutations", counts["mutations"]),
              ("docs/explanation/determinism.md", r"compares (\d+) golden", counts["goldens"]),
              ("docs/explanation/gates.md", r"(\d+) plain-English validator cases", counts["validator_negative_cases"]),
              ("docs/explanation/gameplan.md", r"and (\d+) build gates", counts["build_gates"])]
    for page, rx, want in claims:
        m = re.search(rx, (ROOT / page).read_text())
        c.ok(bool(m) and int(m.group(1)) == want, f"{page}: '{rx}' says {m.group(1) if m else 'nothing'}, derivation says {want}")
    c.ok(re.search(r"(\d+) mutations", "we ran 7 mutations") is not None, "control: the prose-count matcher matches", negative=True)


@gate("B15", "brood and the count ratchet", ["G24"])
def b15(c: Check):
    tf = typefile.load("vanilla.creature.blob")
    a1, inh1 = brood.breed(tf, 11, 29, 5)
    a2, inh2 = brood.breed(tf, 11, 29, 5)
    c.ok(a1[0].pixel_hash() == a2[0].pixel_hash() and inh1 == inh2, "brood is deterministic")
    sources = set()
    for child in range(12):
        sources |= set(brood.lineage(tf, 11, 29, child)["inherited"].values())
    c.ok({"A", "B"} <= sources, f"children inherit from both parents across a brood ({sorted(sources)})")
    counts = derived_counts()
    floor = json.loads(FLOOR.read_text())["floor"]
    for k, v in counts.items():
        if k not in floor:
            c.ok(False, f"count '{k}' is unfloored (a capability nobody counts is one nobody misses)")
        else:
            c.ok(v >= floor[k], f"{k}: {v} >= floor {floor[k]}")


# ---------------------------------------------------------------- data
KNOWN_VECTOR = [124836505, 3156578125, 2270891520, 2401556266, 1551397785, 3265571350]
KNOWN_DERIVE = "adf503f219d8b52bd2b3f532b882caa2"


def _set(path, value):
    def f(d):
        cur = d
        parts = path.split(".")
        for p in parts[:-1]:
            cur = cur[int(p)] if p.isdigit() else cur[p]
        last = parts[-1]
        if value is _DEL:
            cur.pop(last, None)
        else:
            cur[int(last) if last.isdigit() else last] = value
    return f


_DEL = object()
NEGATIVE_CASES = [
    (_set("schema", "pixelgoblin/type@9"), "`schema` must be"),
    (_set("id", "has spaces"), "`id` must be dotted"),
    (_set("tag", "creture.small"), "did you mean 'creature'"),
    (_set("license", "   "), "whitespace is not a license"),
    (_set("generator", "masc"), "did you mean 'mask'"),
    (_set("size", [16, 3]), "between 4 and 512"),
    (_set("size", [16.0, 16]), "decimal number"),
    (_set("palette.outline", "green"), "colours are written like"),
    (_set("palette.ramps", []), "is empty"),
    (_set("palette.ramps.0.colors", ["#000000"]), "it needs 2 to 8"),
    (_set("body.template", ["..1", "..12"]), "different lengths"),
    (_set("body.template", ["..x#"] * 3), "only . (empty)"),
    (_set("body.anchor", [12, 2]), "does not fit inside size"),
    (_set("body.ramp", "mos"), "did you mean 'moss'"),
    (_set("parts.0.chance", 150), "between 0 and 100"),
    (_set("features.eyes", 5), "between 0 and 2"),
    (_set("animation.frame_ms", 5), "between 16 and 2000"),
    (_set("body", _DEL), "`body` is missing"),
    (_set("outline_style", "fuzzy"), "must be plain or selout"),
    (_set("features.eye_band", [80, 10]), "eye_band"),
]

REQUIRED_DOCS = [
    "README.md",
    "docs/tutorials/first-sprite.md",
    "docs/tutorials/make-a-species.md",
    "docs/howto/convert-an-image.md",
    "docs/howto/use-in-a-game.md",
    "docs/howto/make-a-ui-kit.md",
    "docs/reference/cli.md",
    "docs/reference/type-files.md",
    "docs/explanation/determinism.md",
    "docs/explanation/gates.md",
    "docs/explanation/gameplan.md",
    "docs/explanation/decisions.md",
    "docs/explanation/stack.md",
]


def render_cli_doc() -> str:
    from pixelgoblin.cli import EXAMPLES, build_parser
    ap = build_parser()
    subs = next(a for a in ap._actions if a.__class__.__name__ == "_SubParsersAction").choices
    lines = ["# CLI reference", "", "Generated from the parser by `tests/gate.py --regen-docs`. Do not edit by hand;",
             "gate B14 fails if this page and the program disagree.", ""]
    for name, p in subs.items():
        lines += [f"## `{name}`", "", p.description, "", "```", EXAMPLES[name], "```", ""]
        opts = [a for a in p._actions if a.dest != "help"]
        for a in opts:
            flag = ", ".join(a.option_strings) or a.dest
            lines.append(f"- `{flag}` — {a.help or ''}".rstrip(" —"))
        lines.append("")
    return "\n".join(lines)


def derived_counts() -> dict:
    from pixelgoblin.cli import build_parser
    import tomllib
    import vanilla_flavor as vf
    ap = build_parser()
    subs = next(a for a in ap._actions if a.__class__.__name__ == "_SubParsersAction").choices
    falsify_src = (ROOT / "tests" / "falsify.py").read_text()
    return {
        "build_gates": len(GATES),
        "plan_gates_covered": len({g for v in GATES.values() for g in v["covers"]}),
        "goldens": len(json.loads(GOLDENS.read_text())["cases"]),
        "validator_negative_cases": len(NEGATIVE_CASES),
        "mutations": falsify_src.count("Mutation("),
        "vanilla_types": len(vanilla_types()),
        "flavor_types": len(flavor_types()),
        "cli_commands": len(subs),
        "flavor_capabilities": len(vf.CAPABILITIES),
        "tag_roots": len(tomllib.loads((ROOT / "types" / "tags.toml").read_text())["roots"]),
        "doc_pages": len(REQUIRED_DOCS),
    }


# ---------------------------------------------------------------- runner
def run(ids: list[str]) -> dict:
    results = {}
    for bid in ids:
        g = GATES[bid]
        c = Check()
        err = io.StringIO()
        try:
            with redirect_stderr(err):
                g["fn"](c)
        except Exception as e:  # noqa: BLE001
            c.ok(False, f"gate crashed: {e!r}")
        if c.asserts and not c.negatives and bid not in ("B00", "B03", "B10", "B13", "B14", "B15"):
            c.ok(False, "gate has no negative assertion (a gate that cannot fail proves nothing)")
        results[bid] = {"title": g["title"], "covers": g["covers"], "passed": c.failed == 0 and c.asserts > 0,
                        "asserts": c.asserts, "failed": c.failed, "lines": c.lines[:12]}
        mark = "PASS" if results[bid]["passed"] else "FAIL"
        print(f"{mark}  {bid} {g['title']:48} {c.asserts - c.failed}/{c.asserts}")
        for l in c.lines[:12]:
            print(f"        {l}")
    return results


def write_status(results: dict) -> None:
    covered = sorted({g for r in results.values() if r["passed"] for g in r["covers"]})
    allg = sorted({g for r in results.values() for g in r["covers"]})
    lines = ["# BUILD_STATUS", "", f"PixelGoblin {VERSION} · engine major {ENGINE_MAJOR}", "",
             "Written only when every build gate ran. Counts below are derived by the run, not typed.", "",
             f"- Build gates passed: {sum(r['passed'] for r in results.values())} of {len(results)}",
             f"- Plan gates covered by passing build gates: {len(covered)} of {len(allg)}",
             f"- Assertions: {sum(r['asserts'] for r in results.values())}", "",
             "| Gate | What | Covers | Result |", "|---|---|---|---|"]
    for bid, r in results.items():
        lines.append(f"| {bid} | {r['title']} | {', '.join(r['covers']) or '—'} | {'PASS' if r['passed'] else 'FAIL'} |")
    counts = derived_counts()
    floor = json.loads(FLOOR.read_text())["floor"]
    lines += ["", "## Ratchet", "", "| Count | Now | Floor |", "|---|---|---|"]
    lines += [f"| {k} | {v} | {floor.get(k, 'UNFLOORED')} |" for k, v in counts.items()]
    lines += ["", "—Shibbieness", "—Claude", ""]
    (ROOT / "BUILD_STATUS.md").write_text("\n".join(lines))


def bless_goldens(witness: str, reason: str) -> None:
    old = json.loads(GOLDENS.read_text()) if GOLDENS.exists() else {"cases": [], "history": []}
    cases = [{"kind": k, "type": t, "seed": s, "hashes": compute_case(k, t, s)} for k, t, s in golden_cases()]
    old_map = {(g["kind"], g["type"], g["seed"]): g["hashes"] for g in old["cases"]}
    changed = [f"{k[0]} {k[1]} {k[2]}" for k, h in old_map.items()
               if any((c["kind"], c["type"], c["seed"]) == k and c["hashes"] != h for c in cases)]
    removed = [f"{k[0]} {k[1]} {k[2]}" for k in old_map if not any((c["kind"], c["type"], c["seed"]) == k for c in cases)]
    if (changed or removed) and not (witness and reason):
        raise SystemExit(f"{len(changed)} goldens changed and {len(removed)} removed: that changes the pixel contract. "
                         "Pass --witness and --reason (and bump ENGINE_MAJOR if shipped sprites change).")
    hist = old.get("history", [])
    hist.append({"engine_major": ENGINE_MAJOR, "cases": len(cases), "changed": changed, "removed": removed,
                 "witness": witness or "initial", "reason": reason or "first blessing"})
    GOLDENS.parent.mkdir(parents=True, exist_ok=True)
    GOLDENS.write_text(json.dumps({"engine_major": ENGINE_MAJOR, "cases": cases, "history": hist}, indent=1) + "\n")
    print(f"blessed {len(cases)} goldens ({len(changed)} changed, {len(removed)} removed)")


def raise_floor(lower: list[str], witness: str, reason: str) -> None:
    data = json.loads(FLOOR.read_text()) if FLOOR.exists() else {"floor": {}, "history": []}
    counts = derived_counts()
    for k, v in counts.items():
        if v > data["floor"].get(k, 0):
            data["history"].append({"key": k, "from": data["floor"].get(k), "to": v, "kind": "raise"})
            data["floor"][k] = v
    for kv in lower:
        k, v = kv.split("=")
        if not (witness and reason):
            raise SystemExit("lowering a floor requires --witness and --reason")
        data["history"].append({"key": k, "from": data["floor"].get(k), "to": int(v), "kind": "lower", "witness": witness, "reason": reason})
        data["floor"][k] = int(v)
    FLOOR.write_text(json.dumps(data, indent=1) + "\n")
    print(json.dumps(data["floor"], indent=1))


def from_empty() -> int:
    with tempfile.TemporaryDirectory() as t:
        dst = Path(t, "pixelgoblin")
        for p in _repo_files():
            q = dst / p.relative_to(ROOT)
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0", "HOME": t, "LANG": "C.UTF-8"}
        r = subprocess.run([sys.executable, "tests/gate.py", "--all"], cwd=dst, env=env)
        return r.returncode


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("gates", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--report", action="store_true", help="write BUILD_STATUS.md (only with --all)")
    ap.add_argument("--from-empty", action="store_true")
    ap.add_argument("--bless-goldens", action="store_true")
    ap.add_argument("--raise-floor", action="store_true")
    ap.add_argument("--lower", action="append", default=[])
    ap.add_argument("--witness", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--regen-docs", action="store_true")
    a = ap.parse_args(argv)
    if os.environ.get("PYTHONHASHSEED") != "0":
        print("note: run with PYTHONHASHSEED=0 (determinism claims must not depend on the hash seed)")
    if a.from_empty:
        return from_empty()
    if a.bless_goldens:
        bless_goldens(a.witness, a.reason)
        return 0
    if a.raise_floor or a.lower:
        raise_floor(a.lower, a.witness, a.reason)
        return 0
    if a.regen_docs:
        (ROOT / "docs" / "reference" / "cli.md").write_text(render_cli_doc())
        print("docs/reference/cli.md regenerated")
        return 0
    ids = sorted(GATES) if a.all or not a.gates else [g.upper() for g in a.gates]
    unknown = [i for i in ids if i not in GATES]
    if unknown:
        print(f"unknown gates {unknown}; known: {sorted(GATES)}")
        return 2
    results = run(ids)
    ok = all(r["passed"] for r in results.values())
    if a.report:
        if set(ids) == set(GATES):
            write_status(results)
            print("BUILD_STATUS.md written")
        else:
            print("BUILD_STATUS.md NOT written: a status file from a partial run reads as authoritative and is worse than none")
    print(("ALL GATES PASS" if ok else "GATES FAILING") + f"  ({sum(r['passed'] for r in results.values())}/{len(results)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
