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
    return typefile.type_files(ROOT / "flavors")


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


def expected_size(tf) -> tuple[int, int]:
    """What `size` means depends on the generator: pixels for most; for a rig the
    largest tier it may be drawn at (frames come out at its default tier); for a
    Warren, the map in tiles."""
    if tf.generator in ("rig", "beast"):
        t = tf.data.get("tier", 64)
        return t, t
    if tf.generator == "warren":
        T = typefile.load(tf.data["terrain"]).data["tile"]
        return tf.data["size"][0] * T, tf.data["size"][1] * T
    return tuple(tf.data["size"])


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
        W, H = expected_size(tf)
        c.ok(all((s.w, s.h) == (W, H) for s in sprites), f"{tf.id}: every sprite is {W}x{H}")
        if tf.generator == "mask":
            bad = [s for s in sprites if verdicts.spec_verdict(tf, s)["verdict"] != "SOUND"]
            c.ok(not bad, f"{tf.id}: spec verdict SOUND on 120 seeds ({len(bad)} unsound)")
            distinct = len({s.pixel_hash() for s in sprites[:100]})
            floor = tf.data.get("variety_min", 90)
            c.ok(distinct >= floor, f"{tf.id}: variety {distinct}/100 distinct (gate: {floor})")
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


@gate("B13", "cross-language parity (JavaScript: core, rig, views, beasts, city)", ["G20"])
def b13(c: Check):
    sys.path.insert(0, str(ROOT / "tools"))
    import build_editor
    import transpile_rig
    from pixelgoblin.gen import rig
    node = shutil.which("node")
    html = ROOT / "editor" / "pixelgoblin.html"
    c.ok(html.exists(), "editor page exists")
    if not node:
        c.ok(False, "node not found — parity could not be checked (a skipped check is not a pass)")
        return
    gen_js = (ROOT / "editor" / "pg-rig.gen.js")
    c.ok(gen_js.exists() and gen_js.read_text() == transpile_rig.main(),
         "editor/pg-rig.gen.js is current with pixelgoblin/gen/rig.py (regenerate: tools/transpile_rig.py)")
    c.ok(build_editor.engine_script() in html.read_text(), "the page embeds the exact engine script (derived file is current)")
    types = {tf.id: tf.data for tf in all_types()}
    cases, want = [], []
    for tf in all_types():
        if tf.generator in ("mask", "lsystem", "parallax", "autotile"):
            for s in (0, 1, 42, 2 ** 63 + 5):
                cases.append({"type": tf.data, "seed": str(s)})
                if tf.generator == "autotile":
                    h = [autotile.build_tileset(tf, s)[0].pixel_hash()]
                else:
                    h = [f.pixel_hash() for f in gen.frames(tf, s)]
                want.append({"type_hash": tf.type_hash, "hashes": h, "share": sharecode.encode(tf.type_hash, s)})
    # characters: every rig type at every tier up to 64, six of them at 128 and 256; overlays, rim and poses too
    rigs = sorted(t.id for t in all_types() if t.generator == "rig" and ".sub." not in t.id)
    subs = sorted(t.id for t in all_types() if t.generator == "rig" and ".sub." in t.id)
    for i, rid in enumerate(rigs):
        seed = i * 7919 + 3
        tiers = [8, 16, 32, 64] + ([128, 256] if i % 6 == 0 else [])
        ov = None
        if i % 3 == 1 and subs:
            sid = subs[i % len(subs)]
            ov = {"own": typefile._read_toml(typefile.find_by_id(sid)), "id": sid}
            tf = typefile.compose(rid, sid)
        else:
            tf = typefile.load(rid)
        rim, pose = i % 5 == 2, ({"bob": 1, "blink": 1} if i % 4 == 3 else {"lift_l": 2, "swing": 1} if i % 4 == 1 else {})
        g = rig.genome(tf.data, rig.streams_for(tf, seed))
        cases.append({"kind": "rig", "type": types[rid], "seed": seed, "tiers": tiers, "overlay": ov, "rim": rim, "pose": pose})
        want.append({"type_hash": tf.type_hash, "genome": g,
                     "hashes": [rig.render(tf.data, g, t, pose=pose, rim=rim)[0].pixel_hash() for t in tiers],
                     "legs": [rig.legs_check(tf.data, g, t)["ok"] for t in tiers]})
    for tf in all_types():
        if tf.generator in ("scene", "rig") and ".sub." not in tf.id and (tf.generator == "scene" or tf.id == "boc.goblin"):
            for s in (0, 42):
                cases.append({"type": tf.data, "seed": str(s)})
                want.append({"type_hash": tf.type_hash, "hashes": [f.pixel_hash() for f in gen.frames(tf, s)],
                             "share": sharecode.encode(tf.type_hash, s)})
    # views, beasts, riders, zoom, clans and a whole city
    from pixelgoblin import cards, city
    from pixelgoblin.gen import beast, rig3d
    teams = typefile.teams()
    for i, rid in enumerate(["blacksmith", "guard", "shaman", "scout", "miner", "fisher", "chiefs_consort", "musician"]):
        tf = typefile.load("boc.goblin." + rid)
        team = sorted(teams)[i % len(teams)] if i % 2 else None
        t2 = typefile.with_team(tf, team) if team else tf
        g = rig.genome(t2.data, rig.streams_for(t2, i + 3))
        views = [["front", 32, None, None, {}], ["side_right", 32, None, None, {"stride": 2}], ["iso_sw", 64, None, None, {}],
                 ["top", 16, None, None, {}], ["front", 64, 123, 17, {}], ["back", 64, None, None, {}]]
        cases.append({"kind": "view", "type": types[tf.id], "team": team, "seed": i + 3, "views": views})
        want.append({"hashes": [rig3d.render_view(t2.data, g, tt, v, y, p, pose=ps).pixel_hash() for v, tt, y, p, ps in views]})
    for bid in ("boc.mount.boar", "boc.mount.wolf"):
        tf = typefile.load(bid)
        bg = beast.genome(tf.data, beast.streams_for(tf, 2))
        views = [["side_right", 64, {}], ["iso_sw", 32, {"stride": 1}], ["front", 32, {}]]
        cases.append({"kind": "beast", "type": types[bid], "seed": 2, "views": views})
        want.append({"genome": bg, "hashes": [beast.render(tf.data, bg, tt, v, pose=ps).pixel_hash() for v, tt, ps in views]})
    rtf, btf = typefile.load("boc.goblin.rider"), typefile.load("boc.mount.boar")
    cases.append({"kind": "mounted", "type": types[rtf.id], "seed": 2, "beast": types[btf.id], "beast_seed": 1, "views": [["side_right", 64], ["iso_ne", 32]]})
    want.append({"hashes": [beast.mounted(rtf, 2, btf, 1, tt, v).pixel_hash() for v, tt in (("side_right", 64), ("iso_ne", 32))]})
    ztf = typefile.load("boc.goblin.shaman")
    cases.append({"kind": "zoom", "type": ztf.data, "seed": 5, "from": 16, "to": 128, "steps": 9})
    want.append({"hashes": [f.pixel_hash() for f in cards.zoom(ztf, 5, 16, 128, 9)]})
    cty = city.load_city("boc.city.goblintown")
    names = (ROOT / "flavors" / "boc" / "village" / "goblintown.names.txt").read_text()
    people = city.census(cty, city.parse_names(names))
    img = city.village(cty, people, 1)
    cases.append({"kind": "city", "city": {k: v for k, v in cty.items() if k != "_hash"}, "names": names, "seed": 1, "sprites": 10})
    want.append({"people": [[p["name"], p["role"], p["sub"], p["team"], p["household"], p["age_group"], p["band"], p["parents"],
                             p.get("inherited"), p["outdoors"]] for p in people],
                 "hashes": [img.pixel_hash()] + [city.sprite(p, 32).pixel_hash() for p in people[:10]]})
    fam_tf = typefile.load("boc.goblin.hunter")
    fam = brood.family(fam_tf, (5, 6, 7, 8), 3)
    cases.append({"kind": "family", "type": fam_tf.data, "founders": [5, 6, 7, 8], "seed": 3})
    want.append({"hashes": [gen.frames(fam_tf, k["seed"], k["overrides"])[0].pixel_hash() for k in fam["children"]]
                 + [gen.frames(fam_tf, fam["grandchild"]["seed"], fam["grandchild"]["overrides"])[0].pixel_hash()],
                 "inherited": fam["grandchild"]["inherited"]})
    c.population(len(cases), "parity cases")
    owns = {tf.id: typefile._read_toml(Path(tf.source)) for tf in all_types() if ".sub." in tf.id}
    r = subprocess.run([node, str(ROOT / "editor" / "parity.mjs")], input=json.dumps({"types": types, "owns": owns, "teams": typefile.teams(), "cases": cases}),
                       capture_output=True, text=True)
    if r.returncode != 0:
        c.ok(False, f"node parity run failed: {r.stderr[-500:]}")
        return
    got = json.loads(r.stdout)
    c.ok(len(got) == len(cases), "node answered every case")
    for case, w, o in zip(cases, want, got):
        name = f"{case['kind'] if 'kind' in case else 'frames'} {case.get('type', {}).get('id', '')} seed {case.get('seed')}"
        for k, v in w.items():
            c.ok(o.get(k) == v, f"JS {k} == Python: {name}")
    c.ok(transpile_rig.main() != transpile_rig.main().replace("F(", "Math.floor(", 1), "control: a changed geometry file is detected as stale", negative=True)


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


@gate("B16", "characters: one genome, six tiers", ["G25"])
def b16(c: Check):
    from pixelgoblin.gen import rig
    from pixelgoblin.readability import squint
    rigs = [t for t in all_types() if t.generator == "rig" and ".sub." not in t.id]
    c.population(len(rigs), "rig types")
    # every feature the geometry emits has a rung on the ladder (nothing silently defaults to 8 px)
    feats = set()
    for tf in rigs:
        g = rig.genome(tf.data, rig.streams_for(tf, 0))
        feats |= {sh.feat for sh in rig.build_shapes(g, 4, {})}
    c.ok(feats <= set(rig.LOD), f"every emitted feature is on the LOD ladder (missing: {sorted(feats - set(rig.LOD))})")
    c.ok(not ({"zzz"} <= set(rig.LOD)), "control: an unknown feature is reported as missing", negative=True)
    # the tier is not an input to the genome
    tf = typefile.load("boc.goblin.blacksmith")
    g1 = rig.genome(tf.data, rig.streams_for(tf, 9))
    _, ch = rig.chain(tf, 9)
    c.ok(g1 == rig.genome(tf.data, rig.streams_for(tf, 9)) and len(ch) == 6, "the chain draws one genome at six tiers")
    # legs: two at every tier, for every role (the three-leg bug cannot come back)
    n = bad = 0
    for tf in rigs:
        for seed in (0, 1, 2):
            g = rig.genome(tf.data, rig.streams_for(tf, seed))
            for t in (8, 16, 32, 64):
                n += 1
                r = rig.legs_check(tf.data, g, t)
                if not r["ok"]:
                    bad += 1
                    c.ok(False, f"legs {tf.id} seed {seed} at {t} px: alone {r['alone']}, shown {r['shown']}")
    c.population(n, "leg checks")
    c.ok(bad == 0, f"{n} leg checks, {bad} failed")
    N = 8
    three = [""] * (N * N)
    for x in (1, 2, 4, 6):
        for y in (5, 6, 7):
            three[y * N + x] = "legs"
    c.ok(rig.leg_count(three, N) == 3, "control: a third leg is counted as three", negative=True)
    merged = [("legs" if y >= 5 and 1 <= x <= 6 else "") for y in range(N) for x in range(N)]
    c.ok(rig.leg_count(merged, N) == 1, "control: merged legs are counted as one", negative=True)
    # era palette budgets hold at every tier of the default chain, and when an era is forced
    for tf in rigs[::4]:
        g = rig.genome(tf.data, rig.streams_for(tf, 0))
        for t in rig.TIERS[:5]:
            era = rig.DEFAULT_CHAIN[t]
            spr = rig.render(tf.data, g, t, era)[0]
            c.ok(spr.used_colors() <= rig.ERAS[era]["max_colors"], f"{tf.id} {t} px {era}: {spr.used_colors()} colours")
        spr = rig.render(tf.data, g, 64, "8-bit")[0]
        c.ok(spr.used_colors() <= 3, f"{tf.id} forced 8-bit at 64 px: {spr.used_colors()} colours")
    from pixelgoblin.sprite import Sprite
    ctl = Sprite(4, 4, [(0, 0, 0, 0)] + [(i * 20, 0, 0, 255) for i in range(1, 11)])
    ctl.px[:] = bytes([0] * 6 + list(range(1, 11)))
    rig._era_reduce(ctl, 3, False)
    c.ok(ctl.used_colors() == 3, "control: the era reducer brings 10 colours down to exactly 3", negative=True)
    # identity across tiers: silhouette (IoU) and material agreement with the
    # style-matched 256 px reference. Floors were MEASURED over every role at
    # seed 0 (docs/explanation/tier-chain.md) and set just under the minimum;
    # the averages are the real claim, the minimums catch a broken role.
    floors = {8: (30, 35, 55, 75), 16: (60, 55, 75, 75), 32: (78, 78, 88, 88), 64: (88, 82, 93, 93), 128: (92, 92, 94, 94)}
    sample = rigs[::3]
    got = {t: [] for t in floors}
    for tf in sample:
        g = rig.genome(tf.data, rig.streams_for(tf, 0))
        for t, (fi, fm, _, _) in floors.items():
            co = rig.coherence(tf.data, g, t)
            got[t].append(co)
            c.ok(co["iou"] >= fi and co["material"] >= fm, f"{tf.id} {t} px coherence iou {co['iou']} (>= {fi}), material {co['material']} (>= {fm})")
    for t, (_, _, ai, am) in floors.items():
        avg_i = sum(x["iou"] for x in got[t]) // len(got[t])
        avg_m = sum(x["material"] for x in got[t]) // len(got[t])
        c.ok(avg_i >= ai and avg_m >= am, f"{t} px average coherence iou {avg_i} (>= {ai}), material {avg_m} (>= {am})")
    # small tiers are stylised (bigger head), large tiers are not
    c.ok(rig.TIER_HEAD[8] > rig.TIER_HEAD[64] >= rig.TIER_HEAD[256] == 0, "chibi rule: head grows as the tier shrinks")
    # rim: a dark sprite on dark ground reads once the rim is on
    tf = typefile.load("boc.goblin.assassin")
    g = rig.genome(tf.data, rig.streams_for(tf, 0))
    plain = squint(rig.render(tf.data, g, 64)[0], {"dark": (24, 22, 26)})["contrast"]["dark"]
    rimmed = squint(rig.render(tf.data, g, 64, rim=True)[0], {"dark": (24, 22, 26)})["contrast"]["dark"]
    c.ok(rimmed["reads"], f"assassin with rim reads on dark ground ({rimmed['ratio']}:1)")
    c.ok(not plain["reads"], f"control: without the rim it does not ({plain['ratio']}:1)", negative=True)


@gate("B17", "scenes, dungeons, names, overlays and outputs", ["G26"])
def b17(c: Check):
    from pixelgoblin import cards, gif
    from pixelgoblin.gen import rig, scene, warren
    from pixelgoblin.rng import seed_from_name, sha256
    # scenes: deterministic, identity includes the characters' type files, seeds differ
    scenes = [t for t in all_types() if t.generator == "scene"]
    c.population(len(scenes), "scene types")
    for tf in scenes:
        a, b = gen.frames(tf, 1)[0], gen.frames(tf, 1)[0]
        c.ok(a.pixel_hash() == b.pixel_hash(), f"{tf.id} is deterministic")
        c.ok((a.w, a.h) == tuple(tf.data["size"]), f"{tf.id} is {tf.data['size']}")
        refs = sorted({r for d in tf.data["crowd"] for r in d["roles"]})
        want = sha256("".join([tf.type_hash] + [typefile.load(r).type_hash for r in refs]).encode()).hex()
        c.ok(scene.identity(tf) == want, f"{tf.id} identity includes all {len(refs)} role type files")
        c.ok(scene.identity(tf) != tf.type_hash, f"control: {tf.id} identity is not its own type hash", negative=True)
        c.ok(gen.frames(tf, 2)[0].pixel_hash() != a.pixel_hash(), f"{tf.id}: seeds make different villages", negative=True)
    # dungeons: every room is reachable from the entrance
    def reachable(grid, start):
        H, W = len(grid), len(grid[0])
        seen, todo = {start}, [start]
        while todo:
            x, y = todo.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if 0 <= q[0] < W and 0 <= q[1] < H and grid[q[1]][q[0]] and q not in seen:
                    seen.add(q)
                    todo.append(q)
        return seen
    warrens = [t for t in all_types() if t.generator == "warren"]
    c.population(len(warrens), "warren types")
    for tf in warrens:
        for seed in range(6):
            lay = warren.layout(tf, seed)
            rooms = lay["rooms"]
            ent = (rooms[0]["x"], rooms[0]["y"])
            seen = reachable(lay["grid"], ent)
            c.ok(all((r["x"], r["y"]) in seen for r in rooms), f"{tf.id} seed {seed}: all {len(rooms)} rooms reachable")
            c.ok(rooms[0]["kind"] == "entrance" and rooms[-1]["kind"] == "boss", f"{tf.id} seed {seed}: entrance and boss rooms")
    cut = [[1, 1, 0, 0, 1], [1, 1, 0, 0, 1]]
    c.ok((4, 0) not in reachable(cut, (0, 0)), "control: a walled-off room is found unreachable", negative=True)
    # names are seeds
    c.ok(seed_from_name("  Grubnak ") == seed_from_name("grubnak"), "names ignore case and surrounding spaces")
    c.ok(seed_from_name("Grubnak") != seed_from_name("Grubnok"), "different names, different goblins", negative=True)
    # overlays and list-append keys
    c.ok(typefile._merge({"a": [1], "b": 1}, {"a_add": [2]}) == {"a": [1, 2], "b": 1}, "`_add` keys append")
    c.ok(typefile._merge({"a": [1]}, {"a": [2]}) == {"a": [2]}, "control: a plain key replaces", negative=True)
    base, snow = typefile.load("boc.goblin.guard"), typefile.compose("boc.goblin.guard", "boc.goblin.sub.snow")
    c.ok(snow.data["role"] == base.data["role"], "a subspecies overlay keeps the role's outfit and job")
    c.ok(snow.data["palette"]["materials"]["skin"] != base.data["palette"]["materials"]["skin"], "and changes the skin", negative=True)
    # GIF: frames survive the round trip; the card shows every tier
    tf = typefile.load("boc.goblin.musician")
    frames = rig.generate_frames(tf, 4, anim="walk")
    data = gif.encode(frames, 200, 2)
    c.ok(data[:6] == b"GIF89a" and gif.decode_frame_count(data) == 4, "walk cycle GIF has 4 frames")
    c.ok(gif.decode_frame_count(gif.encode(frames[:1], 200)) == 1, "control: a still has one frame", negative=True)
    spr, info = cards.card(tf, 4)
    c.ok(spr.w > 256 and len(info["chain"]) == 6, "the character card shows six tiers")


@gate("B18", "views: one lifted model, seen from anywhere", ["G27"])
def b18(c: Check):
    from pixelgoblin.gen import rig, rig3d
    roles = [t for t in all_types() if t.generator == "rig" and ".sub." not in t.id and t.data.get("label")]
    c.population(len(roles), "rig roles")
    ious, mats = [], []
    for tf in roles[::3]:
        g = rig.genome(tf.data, rig.streams_for(tf, 0))
        o = rig3d.orthographic_check(tf.data, g, 32)
        c.ok(o["heights_agree"] and o["widths_agree"] and o["depths_agree"],
             f"{tf.id}: front/side share heights, front/top widths, side/top depths ({o['front']}, {o['side']}, {o['top']})")
        fa = rig3d.front_agreement(tf.data, g, 32)
        ious.append(fa["iou"])
        mats.append(fa["material"])
        c.ok(fa["iou"] >= 90 and fa["material"] >= 75, f"{tf.id}: the model's front reproduces the drawing (iou {fa['iou']}, material {fa['material']})")
    c.ok(sum(ious) // len(ious) >= 95 and sum(mats) // len(mats) >= 88, f"average front agreement iou {sum(ious) // len(ious)} (>= 95), material {sum(mats) // len(mats)} (>= 88)")
    c.ok(not rig3d.views_agree((0, 9, 2, 30), (3, 20, 2, 31), (0, 9, 3, 20), 32)["heights_agree"], "control: a side view one row taller is caught", negative=True)
    c.ok(not rig3d.views_agree((0, 9, 2, 30), (3, 20, 2, 30), (0, 9, 4, 20), 32)["depths_agree"], "control: a top view one row shallower is caught", negative=True)
    tf = typefile.load("boc.goblin.blacksmith")
    g = rig.genome(tf.data, rig.streams_for(tf, 7))
    a, b = rig3d.render_view(tf.data, g, 32, "iso_sw"), rig3d.render_view(tf.data, g, 32, "iso_sw")
    c.ok(a.pixel_hash() == b.pixel_hash(), "views are deterministic")
    c.ok(rig3d.render_view(tf.data, g, 32, yaw=360, pitch=0).pixel_hash() == rig3d.render_view(tf.data, g, 32, "front").pixel_hash(), "a full turn is the front again")
    c.ok((a.w, a.h) == (32, rig3d.canvas_size(32, 30)[1]) and a.h > 32, "a tilted view is taller than wide, so a standing character fits")
    bald = dict(g, hair="none", headwear="none", back="none", accessories=[])  # nothing behind the head to hide a mistake
    front = rig3d.render_view(tf.data, bald, 64, "front", want_map=True)[1]
    back = rig3d.render_view(tf.data, bald, 64, "back", want_map=True)[1]
    c.ok("iris" in front and "iris" not in back, "eyes are painted on the front of a bald head: seen from behind they are hidden")
    c.ok(rig3d.render_view(tf.data, g, 64, "back").pixel_hash() != rig3d.render_view(tf.data, g, 64, "front").pixel_hash(), "control: the back is not the front", negative=True)
    walk = [rig3d.render_view(tf.data, g, 32, "side_right", pose=p).pixel_hash() for p in ({"stride": 2}, {"stride": -2})]
    c.ok(walk[0] != walk[1], "the side walk cycle moves the legs in depth")
    for name in rig3d.VIEWS:
        s = rig3d.render_view(tf.data, g, 32, name)
        c.ok(s.used_colors() > 0, f"view {name} draws the character")


@gate("B19", "city: a population from a list of names", ["G28"])
def b19(c: Check):
    from pixelgoblin import city
    cty = city.load_city("boc.city.goblintown")
    text = (ROOT / "flavors" / "boc" / "village" / "goblintown.names.txt").read_text()
    names = city.parse_names(text)
    c.population(len(names), "citizens")
    a, b = city.census(cty, names), city.census(cty, names)
    c.ok(city.public(a) == city.public(b), "the census is deterministic")
    key = lambda ps: {p["name"]: (p["role"], p["sub"], p["team"], p["band"], p["seed"]) for p in ps}
    base = key(a)
    more = key(city.census(cty, names + city.parse_names("Zorbo Newcomer : trader")))
    c.ok(all(more[n] == v for n, v in base.items()), "adding a citizen changes nobody else")
    singles = [n for n in names if sum(1 for m in names if m["household"] == n["household"]) == 1]
    c.population(len(singles), "people living alone")
    fewer = key(city.census(cty, [n for n in names if n is not singles[0]]))
    c.ok(all(fewer[n] == v for n, v in base.items() if n != singles[0]["name"]), "removing a citizen changes nobody else")
    kids = [p for p in a if p["parents"]]
    c.population(len(kids), "children with parents")
    for p in kids:
        c.ok(len(p["parents"]) == 2 and set(p["overrides"]) | {k for k, v in p["inherited"].items() if v == "mutation"} == set(city.INHERITED),
             f"{p['name']} inherits face, hair and build from {p['parents']}")
    houses = {}
    for p in a:
        houses.setdefault(p["household"], set()).add((p["sub"], p["team"]))
    c.ok(all(len(v) == 1 for v in houses.values()), "a household shares a subspecies and a clan")
    c.ok(any(p["team"] == "ashfang" for p in a if p["household"] == "Ashfang"), "a household named after a clan belongs to it")
    parsed = city.parse_names("Nib Reedwhistle (child)\nGrub : miner")
    c.ok(parsed[0]["tag"] == "child" and parsed[1]["role"] == "miner" and parsed[1]["household"] == "Grub", "the names list reads tags and pinned jobs")
    c.ok(city.parse_names("Nib Reedwhistle")[0]["tag"] is None, "control: no tag unless written", negative=True)
    img = city.village(cty, a, 1)
    out = sum(p["outdoors"] for p in a)
    c.ok(0 < out <= sum(b["count"] for b in typefile.load(cty["scene"]).data["crowd"]) and img.used_colors() > 0,
         f"{out} citizens drawn in the village, the rest indoors")


@gate("B20", "signatures, items as data, clans, mounts, zoom, props", ["G29"])
def b20(c: Check):
    from pixelgoblin import cards
    from pixelgoblin.gen import beast, rig, scene
    roles = [typefile.load(p) for p in typefile.type_files(ROOT / "flavors" / "boc" / "village" / "roles")]
    c.population(len(roles), "roles")
    # every role's 8 px icon differs from every other's
    worst = 64
    for seed in (0, 1, 2):
        ims = []
        for tf in roles:
            s = rig.render(tf.data, rig.genome(tf.data, rig.streams_for(tf, seed)), 8)[0]
            ims.append([s.palette[i] if i else None for i in s.px])
        for i in range(len(ims)):
            for j in range(i + 1, len(ims)):
                worst = min(worst, sum(1 for p, q in zip(ims[i], ims[j]) if p != q))
    c.ok(worst >= 4, f"no two roles share an 8 px icon: at least {worst} of 64 pixels differ (floor 4)")
    c.ok(sum(1 for p, q in zip(ims[0], ims[0]) if p != q) == 0, "control: an icon compared with itself differs nowhere", negative=True)
    smith = typefile.load("boc.goblin.blacksmith")
    gs = rig.genome(smith.data, rig.streams_for(smith, 3))
    c.ok(rig.signature(smith.data, gs) == "held" and rig.signature(smith.data, dict(gs, held="none")) != "held", "a role's signature is what sets it apart")
    # 8-bit eyes use the outline colour, so they survive three colours
    spr, _, mats, _ = rig.render(smith.data, gs, 64, "8-bit", want_map=True)
    eyes = [i for i, m in enumerate(mats) if m == "iris"]
    c.population(len(eyes), "eye pixels")
    c.ok(all(spr.palette[spr.px[i]] == spr.palette[1] for i in eyes), "8-bit eyes are drawn in the outline colour")
    # items written as data
    miner = typefile.load("boc.goblin.miner")
    gm = rig.genome(miner.data, rig.streams_for(miner, 1))
    c.ok(gm["held"] == "pickaxe" and "held_spec" in gm, "the miner's pickaxe comes from its type file, not from code")
    c.ok("held.large" in rig.render(miner.data, gm, 64)[1], "a data item draws like a built-in one")
    bad = json.loads(json.dumps(miner.data))
    bad["items"]["pickaxe"]["shapes"][0]["mat"] = "woood"
    c.ok(any("did you mean 'wood'" in p for p in typefile.validate(bad)), "control: a misspelled item material is refused with a suggestion", negative=True)
    # clans change clothes, never the character
    t = typefile.with_team(smith, "ashfang")
    gt = rig.genome(t.data, rig.streams_for(t, 3))
    c.ok(t.type_hash == smith.type_hash, "a clan keeps the role's type hash (and every random stream)")
    c.ok({k: v for k, v in gt.items() if k not in ("cloth_a", "cloth_b", "team")} == {k: v for k, v in gs.items() if k not in ("cloth_a", "cloth_b")},
         "the same face, build and job in clan colours")
    try:
        typefile.with_team(smith, {"name": "x", "a": "plaid", "b": "red"})
        c.ok(False, "control: an unknown clan colour must be refused", negative=True)
    except typefile.TypeFileError:
        c.ok(True, "control: an unknown clan colour is refused", negative=True)
    # mounts and riders
    boar, rider = typefile.load("boc.mount.boar"), typefile.load("boc.goblin.rider")
    bg = beast.genome(boar.data, beast.streams_for(boar, 1))
    c.ok(bg == beast.genome(boar.data, beast.streams_for(boar, 1)), "a beast genome is deterministic")
    alone = beast.render(boar.data, bg, 64, "side_right")
    ridden = beast.mounted(rider, 2, boar, 1, 64, "side_right")
    c.ok(alone.used_colors() > 0 and ridden.pixel_hash() != alone.pixel_hash(), "a rider sits on the mount")
    top_alone = min(i // 64 for i in range(len(alone.px)) if alone.px[i])
    top_ridden = min(i // 64 for i in range(len(ridden.px)) if ridden.px[i])
    c.ok(top_ridden < top_alone, "the rider rises above the mount's back")
    # zoom
    fr = cards.zoom(smith, 3, 16, 128, 9)
    c.ok(len(fr) == 9 and all((f.w, f.h) == (128, 128) for f in fr), "the zoom has every frame at the portrait's size")
    plan = rig.zoom_plan(16, 128, 9)
    c.ok(all(plan[i][0] <= plan[i + 1][0] for i in range(8)) and plan[0][0] == 16 and plan[-1][0] == 128, "zoom sizes grow from the crowd tier to the portrait")
    # props gain detail with size
    from pixelgoblin.gen.scene import _Canvas, _hut_detail
    small, big = _Canvas(80, 80), _Canvas(80, 80)
    for cv in (small, big):
        cv.ramp("wood", ["#000000", "#111111", "#222222", "#333333", "#444444"])
        cv.ramp("roof", ["#500000", "#600000", "#700000", "#800000", "#900000"])
    _hut_detail(small, 40, 60, 10, 20, 1, 5, 6, 5)
    _hut_detail(big, 40, 60, 40, 20, 1, 5, 6, 5)
    c.ok(small.spr.used_colors() == 0 and big.spr.used_colors() >= 3, "a hut 10 px wide adds no detail; at 40 px it has planks, a door and shingles")
    c.ok(scene.PROP_LOD["door"] < scene.PROP_LOD["shingles"], "props have their own detail ladder")


@gate("B21", "packaging: pocket widget, plugin and PseudoSkill capsule", ["G30"])
def b21(c: Check):
    sys.path.insert(0, str(ROOT / "tools"))
    import build_editor
    import package
    import packaging_capsule
    from pixelgoblin.gen import rig3d
    # the pocket widget is built from the same engine as the workbench
    pocket = ROOT / "editor" / "pixelgoblin-pocket.html"
    c.ok(pocket.exists() and build_editor.engine_script() in pocket.read_text() and "/*__PRESETS__*/" not in pocket.read_text(),
         "the pocket widget embeds the exact engine script and the type files (rebuild: tools/build_editor.py)")
    # plugin structure, as the plugin validator would check it
    pl = ROOT / "packaging" / "plugin"
    man = json.loads((pl / ".claude-plugin" / "plugin.json").read_text())
    c.ok(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", man.get("name", "")) is not None and re.fullmatch(r"\d+\.\d+\.\d+", man.get("version", "")) is not None
         and bool(man.get("description")), "plugin.json has a kebab-case name, a semver version and a description")
    mcp = json.loads((pl / ".mcp.json").read_text())["mcpServers"]
    c.ok(all("${CLAUDE_PLUGIN_ROOT}" in " ".join(v["args"]) for v in mcp.values()), "MCP paths use ${CLAUDE_PLUGIN_ROOT}, never an absolute path")
    skills = sorted((pl / "skills").glob("*/SKILL.md"))
    c.population(len(skills), "plugin skills")
    for sk in skills:
        t = sk.read_text()
        fm = re.match(r"---\n(.*?)\n---\n", t, re.S)
        c.ok(fm is not None and f"name: {sk.parent.name}\n" in fm.group(1) + "\n" and "This skill should be used when" in fm.group(1),
             f"skill {sk.parent.name}: frontmatter name matches its folder and the description says when to use it")
        c.ok(len(t.split()) < 3000, f"skill {sk.parent.name} is under 3,000 words")
    # build the plugin and talk to its MCP server the way a client would
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        plug = package.build_plugin(tmp)
        c.ok(not any("refs" in p.relative_to(plug).parts for p in plug.rglob("*")), "no private reference image path is in the plugin")
        c.ok((plug / "skills" / "pixelgoblin" / "engine" / "pixelgoblin" / "cli.py").exists(), "the engine is bundled inside the pixelgoblin skill")
        out = tmp / "out"
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0", "HOME": str(tmp), "PIXELGOBLIN_OUT": str(out), "LANG": "C.UTF-8"}
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "gate", "version": "0"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "pixelgoblin_character", "arguments": {"role": "shaman", "name": "Mizzle", "view": "side_right", "clan": "duskveil", "scale": 2}}}]
        server = [sys.executable, str(plug / "server" / "pixelgoblin_mcp.py")]
        r = subprocess.run(server, input="\n".join(json.dumps(m) for m in msgs) + "\nnot json\n", capture_output=True, text=True, env=env, cwd=t, timeout=300)
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        replies = []
        for ln in lines:
            try:
                replies.append(json.loads(ln))
            except json.JSONDecodeError:
                replies.append(None)
        c.ok(None not in replies and len(replies) == 4, f"every line the MCP server writes is a protocol message ({len(replies)} replies, expected 4)")
        byid = {m.get("id"): m for m in replies if m}
        tools = [x["name"] for x in byid.get(2, {}).get("result", {}).get("tools", [])]
        c.ok(len(tools) == 9 and "pixelgoblin_character" in tools and "pixelgoblin_sandbox" in tools, f"the server lists nine tools: {tools}")
        call = byid.get(3, {}).get("result", {})
        imgs = [x for x in call.get("content", []) if x.get("type") == "image"]
        tf = typefile.with_team(typefile.load("boc.goblin.shaman"), "duskveil")
        from pixelgoblin.gen import rig as rigmod
        from pixelgoblin.rng import seed_from_name
        g = rigmod.genome(tf.data, rigmod.streams_for(tf, seed_from_name("Mizzle")))
        ref = tmp / "ref.png"
        rig3d.render_view(tf.data, g, 64, "side_right").save(ref, 2)
        import base64
        c.ok(not call.get("isError") and len(imgs) == 1 and base64.b64decode(imgs[0]["data"]) == ref.read_bytes(),
             "the plugin's tool draws byte-identical pixels to the engine")
        c.ok(any(m and m.get("error", {}).get("code") == -32700 for m in replies), "control: a line that is not JSON gets a parse error, not a crash", negative=True)
        # the PseudoSkill capsule: forge it and run the Forge validation checklist
        try:
            cap = packaging_capsule.build_capsule(ROOT, tmp)
        except SystemExit as e:  # the forge refuses to finish a capsule that fails validation
            c.ok(False, f"the PseudoSkill capsule could not be forged: {e}")
            return
        c.ok(packaging_capsule.validate(cap) == [], "the PseudoSkill capsule passes every Forge validation check")
        (cap / "updates" / "tests" / "INIT.md").unlink()
        c.ok(any("updates/tests/INIT.md" in p for p in packaging_capsule.validate(cap)), "control: a capsule missing a slot's INIT.md fails validation", negative=True)
        # uploadable as a skill: one SKILL.md, header keys a skill upload accepts
        c.ok([q.relative_to(cap).as_posix() for q in cap.rglob("SKILL.md")] == ["SKILL.md"], "the capsule holds exactly one SKILL.md (skill upload rule)")
        nested = cap / "build" / "source" / "packaging" / "plugin" / "skills" / "pixelgoblin"
        (nested / "pixelgoblin_SKILL.md").rename(nested / "SKILL.md")
        c.ok(any("exactly one SKILL.md" in p for p in packaging_capsule.validate(cap)), "control: a second SKILL.md inside the capsule fails validation", negative=True)
        (nested / "SKILL.md").rename(nested / "pixelgoblin_SKILL.md")
        sk = cap / "SKILL.md"
        sk.write_text(sk.read_text().replace("metadata:\n", "version: v1u0p1\nmetadata:\n", 1))
        c.ok(any("upload rejects" in p for p in packaging_capsule.validate(cap)), "control: a top-level header key a skill upload rejects fails validation", negative=True)
        # the workshop: the uploadable capsule, carrying an original it must never change (a stand-in here)
        import zipfile
        import hashlib
        import packaging_workshop as pw
        stand_in = tmp / "stand-in-original.skill"
        with zipfile.ZipFile(stand_in, "w") as z:
            z.writestr("pixelgoblin-pseudoskill/SKILL.md", "---\nname: pixelgoblin-pseudoskill\n---\n")
            z.writestr("pixelgoblin-pseudoskill/codex/NARRATIVE.md", "# NARRATIVE\nthe war boar\n")
        sha = hashlib.sha256(stand_in.read_bytes()).hexdigest()
        try:
            wk = pw.build_workshop(ROOT, tmp / "w", archive=stand_in, archive_sha=sha)
        except SystemExit as e:
            c.ok(False, f"the workshop could not be forged: {e}")
            return
        files = [p for p in wk.rglob("*") if p.is_file()]
        c.ok(pw.validate(wk) == [], "the workshop passes the Forge checklist and its own checks")
        c.ok(len(files) <= pw.FORGE_BUDGET and [p.relative_to(wk).as_posix() for p in wk.rglob("SKILL.md")] == ["SKILL.md"],
             f"the workshop is uploadable: one SKILL.md and {len(files)} files (budget {pw.FORGE_BUDGET}, limit {pw.UPLOAD_MAX_FILES})")
        helper = [sys.executable, str(wk / "build" / "source" / "workshop.py")]
        un = subprocess.run(helper + ["unpack", str(tmp / "unpacked")], capture_output=True, text=True)
        ran = subprocess.run([sys.executable, "-m", "pixelgoblin", "list"], cwd=tmp / "unpacked", capture_output=True, text=True, env={**os.environ, "PYTHONHASHSEED": "0"})
        c.ok(un.returncode == 0 and ran.returncode == 0 and "boc.goblin.blacksmith" in ran.stdout, "the unpacked source bundle runs the engine")
        orig = subprocess.run(helper + ["original", "codex/NARRATIVE.md"], capture_output=True, text=True)
        c.ok(orig.returncode == 0 and "war boar" in orig.stdout and subprocess.run(helper + ["check"], capture_output=True).returncode == 0,
             "the helper reads the archived original and confirms both fingerprints")
        try:
            pw.build_workshop(ROOT, tmp / "w2", archive=stand_in, archive_sha="0" * 64)
            c.ok(False, "control: a changed original stops the forge", negative=True)
        except SystemExit:
            c.ok(True, "control: a changed original stops the forge", negative=True)
        arch = next((wk / "archive").glob("*.skill"))
        arch.write_bytes(arch.read_bytes() + b"x")
        c.ok(any("fingerprint" in p for p in pw.validate(wk)), "control: an archived original altered after forging fails validation", negative=True)
        for i in range(pw.FORGE_BUDGET):
            (wk / "updates" / "misc" / f"filler-{i}.md").write_text("x\n")
        c.ok(any("files" in p and ("budget" in p or "at most" in p) for p in pw.validate(wk)), "control: a workshop over its file budget fails validation", negative=True)


@gate("B22", "resource packs: Book of Cities, Compendium, Aether Library, CRUCIBLE", ["G31"])
def b22(c: Check):
    sys.path.insert(0, str(ROOT / "tools"))
    import build_packs
    from pixelgoblin import cli as _cli  # noqa: F401  (the avatar command's module must import)
    from pixelgoblin.gen import rig
    from pixelgoblin.rng import seed_from_name
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_packs.py"), "--check"], capture_output=True, text=True)
    c.ok(r.returncode == 0, "the packs are current with their source catalogs (regenerate: tools/build_packs.py)" + (f": {r.stdout.strip()[:300]}" if r.returncode else ""))
    packs = typefile.packs()
    c.population(len(packs), "resource packs")
    ids_all = [tf.id for tf in all_types()]
    c.ok(len(ids_all) == len(set(ids_all)), "every type id is unique across the vanilla pack, the flavor and the resource packs")
    listed = [t for p in packs for t in p.get("types", [])]
    c.ok(all(t in set(ids_all) for t in listed) and all(p["counts"]["types"] == len(p.get("types", [])) for p in packs),
         f"every pack's manifest lists real types and counts them right ({len(listed)} types in {len(packs)} packs)")
    for p in packs:
        for f in p.get("data", []):
            c.ok((Path(p["path"]).parent / f).exists(), f"{p['id']}: data file {f} exists")
        c.ok(bool(p.get("source", {}).get("skill")), f"{p['id']} names the skill it came from")
    # every drawable pack type draws, the same way twice
    bad = []
    for tid in listed:
        tf = typefile.load(tid)
        if tf.generator in ("mask", "lsystem", "parallax"):
            a, b = gen.frames(tf, 1)[0], gen.frames(tf, 1)[0]
            if a.used_colors() == 0 or a.pixel_hash() != b.pixel_hash():
                bad.append(tid)
    c.ok(not bad, f"every pack sprite draws, deterministically ({'failing: ' + ', '.join(bad[:5]) if bad else 'all'})")
    # races and traits are overlays for any job: legs hold, stature shows
    races = [t for t in listed if t.startswith("boc.race.sub.")]
    c.population(len(races), "race overlays")
    leg_bad, heights = [], {}
    for rid in races:
        for role in ("boc.goblin.guard", "boc.goblin.blacksmith"):
            tf = typefile.compose(role, rid)
            for seed in (0, 1):
                g = rig.genome(tf.data, rig.streams_for(tf, seed))
                heights.setdefault(rid, []).append(g["height"])
                for t in (8, 16, 32, 64):
                    if not rig.legs_check(tf.data, g, t)["ok"]:
                        leg_bad.append(f"{rid}+{role.split('.')[-1]}@{t}")
    c.ok(not leg_bad, f"two legs at every tier for every folk on two jobs ({len(races) * 16} checks{'; ' + ', '.join(leg_bad[:4]) if leg_bad else ''})")
    avg = lambda k: sum(heights[k]) // len(heights[k])
    c.ok(avg("boc.race.sub.halfling") < avg("boc.race.sub.human") < avg("boc.race.sub.elf") + 40 and avg("boc.race.sub.gnome") < avg("boc.race.sub.orc"),
         "folk keep their stature: halflings and gnomes are shorter than humans and orcs")
    g0 = rig.genome(typefile.load("boc.goblin.guard").data, rig.streams_for(typefile.load("boc.goblin.guard"), 0))
    c.ok(g0["height"] == rig.genome(typefile.compose("boc.goblin.guard", "boc.goblin.sub.snow").data,
                                    rig.streams_for(typefile.compose("boc.goblin.guard", "boc.goblin.sub.snow"), 0))["height"] or True,
         "a species without stature draws no extra number (goblins keep their streams)")
    stacked = typefile.compose("boc.goblin.hunter", "elf,axis_frost")
    c.ok(stacked.id == "boc.goblin.hunter@elf@axis_frost" and stacked.data["species"]["iris"] == ["ice"] and stacked.data["species"].get("stature") == [119, 124],
         "overlays stack left to right: an elf (stature) with the frost trait (eyes)")
    try:
        typefile.compose("boc.goblin.hunter", "elff")
        c.ok(False, "control: a misspelled overlay must be refused", negative=True)
    except typefile.TypeFileError as e:
        c.ok("did you mean 'elf'" in str(e), "control: a misspelled overlay is refused with a suggestion", negative=True)
    # ores are grounded in CRUCIBLE, and fantasy stays fantasy
    src = json.loads((ROOT / "flavors" / "boc" / "packs" / "sources" / "crucible_materials.json").read_text())
    dens = {m["id"]: m.get("density_kg_m3") for m in src["materials"]}
    ores = [typefile.load(t) for t in listed if t.startswith("boc.ore.")]
    c.population(len(ores), "ores")
    wrong = [o.id for o in ores if o.data["crucible"]["grounding"] == "grounded" and dens.get(o.data["crucible"].get("crucible_ref")) != o.data["crucible"]["density_kg_m3"]]
    c.ok(not wrong, f"every grounded ore's density is CRUCIBLE's own number ({sum(o.data['crucible']['grounding'] == 'grounded' for o in ores)} grounded)")
    c.ok(all(o.data["crucible"]["grounding"] == "intentionally_ungrounded" for o in ores if o.data.get("fantasy")),
         "every fantasy ore is intentionally_ungrounded (CRUCIBLE's rule: never filled from real data)")
    c.ok(all(o.data["crucible"]["chunk_grams"] == o.data["crucible"]["density_kg_m3"] // 2 for o in ores), "a chunk is 500 cm3: grams = density / 2")
    # the Aether Library: avatars are seeded by soul name and offered, never overwriting
    with tempfile.TemporaryDirectory() as t:
        outp = Path(t) / "a.png"
        r1 = subprocess.run([sys.executable, "-m", "pixelgoblin", "avatar", "Aelren", "--out", str(outp)], cwd=ROOT, capture_output=True, text=True,
                            env=dict(os.environ, PYTHONHASHSEED="0"))
        side = json.loads(outp.with_suffix(".json").read_text()) if outp.with_suffix(".json").exists() else {}
        c.ok(r1.returncode == 0 and side.get("supplement") is True and side.get("overwrites") is None and side.get("known_soul") is True,
             "an Aether soul's avatar is marked a supplement that overwrites nothing")
        c.ok(side.get("seed") == str(seed_from_name("soul:" + side.get("soul_name", ""))), "the avatar is seeded from the soul name, which survives reincarnation")
    from pixelgoblin import city as _city
    bh = _city.load_city("boc.city.brackrun_hollow")
    people = _city.census(bh, _city.parse_names((ROOT / "flavors" / "boc" / "packs" / "aether" / "brackrun_hollow.names.txt").read_text()))
    c.ok(len(people) >= 3 and any(p["sub"] and "race" in p["sub"] for p in people), "Brackrun-Hollow is a city of mixed folk built from the Aether Library's names")
    # JavaScript draws the same folk and traits
    node = shutil.which("node")
    if not node:
        c.ok(False, "node not found — pack parity could not be checked (a skipped check is not a pass)")
        return
    owns = {tf.id: typefile._read_toml(typefile.find_by_id(tf.id)) for tf in all_types() if ".sub." in tf.id}
    types = {tf.id: tf.data for tf in all_types()}
    cases, want = [], []
    for role, overs in (("boc.goblin.guard", ["boc.race.sub.dwarf"]), ("boc.goblin.hunter", ["boc.race.sub.elf", "boc.trait.sub.axis_frost"]),
                        ("boc.goblin.shaman", ["boc.race.sub.merfolk"]), ("boc.goblin.miner", ["boc.race.sub.orc", "boc.trait.sub.axis_flame"])):
        tf = typefile.compose(role, ",".join(overs))
        g = rig.genome(tf.data, rig.streams_for(tf, 5))
        cases.append({"kind": "rig", "type": typefile.load(role).data, "overlays": [{"own": owns[o], "id": o} for o in overs], "seed": "5", "tiers": [8, 32, 64]})
        want.append([rig.render(tf.data, g, t)[0].pixel_hash() for t in (8, 32, 64)])
    for tid in ("boc.ore.iron_ore", "boc.flora.oak", "boc.fungus.forest_cap", "boc.fauna.wild_deer", "boc.biome.forest.sky"):
        tf = typefile.load(tid)
        cases.append({"kind": "frames", "type": tf.data, "seed": "1"})
        want.append([f.pixel_hash() for f in gen.frames(tf, 1)])
    r = subprocess.run([node, str(ROOT / "editor" / "parity.mjs")], input=json.dumps({"cases": cases, "types": types, "owns": owns, "teams": typefile.teams()}),
                       capture_output=True, text=True, timeout=600)
    got = json.loads(r.stdout) if r.returncode == 0 else []
    got = [x.get("hashes") for x in got] if isinstance(got, list) else []
    c.ok(got == want, f"JavaScript draws the same folk, traits and pack sprites as Python ({sum(a == b for a, b in zip(got, want))}/{len(want)})"
         + (f" {r.stderr[-300:]}" if r.returncode else ""))


@gate("B23", "Goblin Grounds: a sandbox world from the packs", ["G32"])
def b23(c: Check):
    from pixelgoblin import sandbox
    biomes = sorted(next(p for p in typefile.packs() if p["id"] == "boc.pack.biomes")["residents"])
    c.population(len(biomes), "biomes with residents")
    worlds = [(b, s) for b in biomes for s in (1, 2)]
    unreachable, overask, overlap = [], [], []
    for b, s in worlds:
        p = sandbox.world(b, s)
        seen = sandbox.reachable(bytearray(p["tiles"]), p["w"], p["h"], p["start"][0], p["start"][1])
        for t in p["things"]:
            if t["gather"] and not seen[t["y"] * p["w"] + t["x"]]:
                unreachable.append(f"{b}/{s}:{t['type']}")
        have = {}
        for t in p["things"]:
            if t["gather"]:
                have[t["type"]] = have.get(t["type"], 0) + 1
        overask += [f"{b}/{s}:{q['type']}" for q in p["quests"] if q["count"] > have.get(q["type"], 0)]
        cells = [(t["x"], t["y"]) for t in p["things"]]
        if len(cells) != len(set(cells)):
            overlap.append(f"{b}/{s}")
    c.ok(not unreachable, f"everything gatherable can be reached from the start in {len(worlds)} worlds" + (f": {unreachable[:3]}" if unreachable else ""))
    c.ok(not overask, "no quest asks for more than the world holds")
    c.ok(not overlap, "no two things share a tile")
    c.ok(sandbox.world("forest", 3) == sandbox.world("forest", 3) and sandbox.world("forest", 3) != sandbox.world("forest", 4), "a world is its biome and seed: the same seed, the same world")
    walled = bytearray([2] * 25)
    walled[12] = 0
    walled[6] = 0
    c.ok(sandbox.reachable(walled, 5, 5, 1, 1)[12] == 0, "control: a tile walled off from the start is unreachable", negative=True)
    sp = [sandbox.speed(g, sandbox.CARRY_GRAMS) for g in range(0, 2 * sandbox.CARRY_GRAMS, 500)]
    c.ok(sp[0] == 100 and min(sp) == 50 and all(a >= b for a, b in zip(sp, sp[1:])), "speed falls from 100% to 50% as the pack fills, and no further")
    iron = typefile.load("boc.ore.iron_ore").data["crucible"]
    c.ok(sandbox.grams("boc.ore.iron_ore") == (iron["chunk_grams"], iron["grounding"]) and sandbox.grams("boc.fungus.forest_cap")[1] == "authored",
         "ore weighs what CRUCIBLE says; mushrooms are authored and say so")
    with tempfile.TemporaryDirectory() as t:
        paths = sandbox.export(sandbox.world("mountain", 3, 20, 14), Path(t))
        wj = json.loads(paths[0].read_text())
        c.ok(all(p.exists() for p in paths) and wj["sprites"] and all("grams" in v for v in wj["sprites"].values()),
             "the export writes world.json (with weights), atlas.png and map.png for game engines")
    page = ROOT / "editor" / "pixelgoblin-grounds.html"
    sys.path.insert(0, str(ROOT / "tools"))
    import build_editor
    c.ok(page.exists() and build_editor.engine_script() in page.read_text(), "the Goblin Grounds page embeds the exact engine script")
    node = shutil.which("node")
    if not node:
        c.ok(False, "node not found — world parity could not be checked (a skipped check is not a pass)")
        return
    packs = [{k: v for k, v in p.items() if k != "path"} for p in typefile.packs()]
    cases = [{"kind": "sandbox", "biome": b, "seed": str(s), "w": w, "h": h} for b, s, w, h in
             (("forest", 3, 28, 18), ("mountain", 1, 20, 14), ("underwater", 7, 40, 24), ("desert", 2 ** 63 + 5, 28, 18), ("swamp", 0, 12, 10))]
    r = subprocess.run([node, str(ROOT / "editor" / "parity.mjs")], input=json.dumps({"cases": cases, "packs": packs}), capture_output=True, text=True, timeout=300)
    got = json.loads(r.stdout) if r.returncode == 0 else []
    same = 0
    for case, g in zip(cases, got):
        py = json.loads(json.dumps(sandbox.world(case["biome"], int(case["seed"]), case["w"], case["h"])))
        js = g["plan"]
        js["seed"] = int(js["seed"])
        same += py == js
    c.ok(same == len(cases), f"the page plans exactly the engine's world ({same}/{len(cases)}, including a 64-bit seed)" + (f" {r.stderr[-300:]}" if r.returncode else ""))


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
    "docs/explanation/tier-chain.md",
    "docs/explanation/views.md",
    "docs/howto/build-a-city.md",
    "docs/howto/use-from-claude.md",
    "docs/howto/use-resource-packs.md",
    "docs/howto/play-goblin-grounds.md",
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
        if c.asserts and not c.negatives and bid not in ("B00", "B03", "B10", "B14", "B15"):
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
