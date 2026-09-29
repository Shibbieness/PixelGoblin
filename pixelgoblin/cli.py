"""pixelgoblin — command line.

Every command prints plain-language help with at least one example
(`pixelgoblin <command> --help`), exits non-zero on error, and writes a
provenance record next to what it makes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import CREDIT, VERSION, brood, cards, export, gen, gif, hazard, readability, sharecode, typefile, uikit, verdicts
from .gen import rig
from .rng import seed_from_name
from .convert import convert_file, likeness
from .sprite import Sprite
from .tiles import autotile, wfc

EXAMPLES = {
    "gen": "pixelgoblin gen types/vanilla/creature.blob.toml --seed 42 --out blob.png --scale 4",
    "sheet": "pixelgoblin sheet vanilla.creature.blob --seeds 0-63 --out blobs.png --scale 3",
    "anim": "pixelgoblin anim vanilla.creature.blob --seed 7 --out blob_idle.png",
    "convert": "pixelgoblin convert photo.png --tag creature.small --out small.png --scale 4",
    "likeness": "pixelgoblin likeness frog.png --tag creature.small --id my.creature.frog --out frog.toml",
    "autotile": "pixelgoblin autotile vanilla.terrain.grass --seed 1 --out grass_tiles.png",
    "wfc": "pixelgoblin wfc sample.png --size 48x48 --seed 3 --out floor.png",
    "uikit": "pixelgoblin uikit vanilla.ui.stone --seed 1 --out kit/",
    "validate": "pixelgoblin validate types/ flavors/",
    "share": "pixelgoblin share vanilla.creature.blob --seed 42      |   pixelgoblin share --decode PG-...",
    "brood": "pixelgoblin brood vanilla.creature.blob 11 29 --child 5 --out kid.png --scale 4",
    "verdict": "pixelgoblin verdict vanilla.creature.blob --seed 42 --target nes",
    "ascii": "pixelgoblin ascii vanilla.creature.blob --seed 42 --out blob.txt",
    "list": "pixelgoblin list",
    "card": "pixelgoblin card boc.goblin.village_chief --name Grubnak --out chief_card.png",
    "chain": "pixelgoblin chain boc.goblin.blacksmith --seed 3 --out smith/   (+ --sub snow, --era 8-bit)",
    "roster": "pixelgoblin roster flavors/boc/village/roles --tier 64 --seed 1 --out roster.png --sub cave",
    "gif": "pixelgoblin gif boc.goblin.musician --seed 2 --anim walk --tier 64 --out walk.gif --scale 2",
    "squint": "pixelgoblin squint boc.goblin.assassin --seed 1 --tier 32",
    "family": "pixelgoblin family vanilla.creature.blob 11 29 40 57 --out family.png --scale 4",
    "watch": "pixelgoblin watch ./dropzone --once     (frog.png + frog.tag containing creature.small)",
    "view": "pixelgoblin view boc.goblin.guard --name Brakka --view iso_sw --tier 64 --out brakka_iso.png --scale 4   (or --yaw 120 --pitch 20)",
    "turnaround": "pixelgoblin turnaround boc.goblin.scout --seed 3 --pitch 30 --tier 64 --out scout_8dir.png --scale 2",
    "expressions": "pixelgoblin expressions boc.goblin.musician --seed 4 --tier 128 --out faces.png",
    "clans": "pixelgoblin clans boc.goblin.guard --seed 2 --out clans.png --scale 2",
    "zoom": "pixelgoblin zoom boc.goblin.shaman --seed 5 --from 16 --to 256 --out zoom.gif",
    "ride": "pixelgoblin ride boc.goblin.rider boc.mount.boar --seed 2 --mount-seed 1 --view side_right --tier 128 --out rider.png --scale 2",
    "city": "pixelgoblin city boc.city.goblintown flavors/boc/village/goblintown.names.txt --out town/",
    "packs": "pixelgoblin packs",
    "pack": "pixelgoblin pack boc.pack.ores --out ores.png --scale 3",
    "avatar": "pixelgoblin avatar Aelren --view iso_sw --out aelren.png --scale 3",
    "sandbox": "pixelgoblin sandbox --biome mountain --seed 3 --out grounds/",
}


def _seeds(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def _seed(a) -> int:
    name = getattr(a, "name", None)
    return seed_from_name(name) if name else getattr(a, "seed", 0)


def _load(a):
    """A type id or path, optionally with a variant overlay (--sub snow) and clan colours (--team ashfang)."""
    sub = getattr(a, "sub", None)
    tf = typefile.compose(a.type, sub) if sub else typefile.load(a.type)
    team = getattr(a, "team", None)
    return typefile.with_team(tf, team) if team else tf


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _say_findings(findings) -> None:
    for f in findings:
        print(f"\n!! {f.kind} ({f.severity}, {f.status})\n   {f.mechanism}\n", file=sys.stderr)


def cmd_gen(a):
    tf = _load(a)
    a.seed = _seed(a)
    if tf.generator == "rig":
        g = rig.genome(tf.data, rig.streams_for(tf, a.seed))
        s = rig.render(tf.data, g, a.tier or tf.data.get("tier", 64), a.era, rim=a.rim)[0]
    else:
        s = gen.sprite(tf, a.seed)
    s.save(a.out, a.scale)
    _write_json(Path(a.out).with_suffix(".json"), export.provenance(tf, a.seed, pixel_hash=s.pixel_hash(), share=sharecode.encode(tf.type_hash, a.seed)))
    print(f"{a.out}  {s.w}x{s.h}  {s.used_colors()} colours  share {sharecode.encode(tf.type_hash, a.seed)}")


def cmd_sheet(a):
    tf = typefile.load(a.type)
    seeds = _seeds(a.seeds)
    sprites = [gen.sprite(tf, s) for s in seeds]
    export.contact_sheet(sprites, a.cols).save(a.out, a.scale)
    distinct = len({s.pixel_hash() for s in sprites})
    _write_json(Path(a.out).with_suffix(".json"), export.provenance(tf, None, seeds=a.seeds, distinct=distinct))
    print(f"{a.out}  {len(sprites)} sprites, {distinct} distinct")


def cmd_anim(a):
    tf = typefile.load(a.type)
    frames = gen.frames(tf, a.seed)
    ms = tf.data.get("animation", {}).get("frame_ms", 200)
    found = hazard.flash_check(frames, ms)
    prov = export.provenance(tf, a.seed, hazards=[f.__dict__ for f in found])
    img, meta = export.sheet(frames, tf.id, ms, Path(a.out).name, prov)
    img.save(a.out, a.scale)
    _write_json(Path(a.out).with_suffix(".json"), meta)
    _say_findings(found)
    print(f"{a.out}  {len(frames)} frames @ {ms} ms" + ("  (hazard reported)" if found else ""))


def cmd_convert(a):
    over = {}
    for kv in a.set or []:
        k, v = kv.split("=", 1)
        over[k] = int(v) if v.isdigit() else v
    s, rep = convert_file(a.image, a.tag, over)
    s.save(a.out, a.scale)
    _write_json(Path(a.out).with_suffix(".json"), export.provenance(None, None, source=str(a.image), conversion=rep, pixel_hash=s.pixel_hash()))
    print(f"{a.out}  {s.w}x{s.h}  {rep.get('colors_used', 0)} colours  profile {a.tag}")


def cmd_likeness(a):
    s, rep = convert_file(a.image, a.tag, {})
    text = likeness(s, a.id, a.tag)
    Path(a.out).write_text(text, encoding="utf-8")
    typefile.load(a.out)  # prove it validates
    print(f"{a.out}  learned a type file; try: pixelgoblin sheet {a.out} --seeds 0-31 --out like.png --scale 3")


def cmd_autotile(a):
    tf = typefile.load(a.type)
    sheet, masks = autotile.build_tileset(tf, a.seed)
    sheet.save(a.out, a.scale)
    table = autotile.index_table()
    _write_json(Path(a.out).with_suffix(".json"), {"tile": tf.data["tile"], "columns": autotile.COLS,
                                                   "blob_masks": masks, "raw_to_tile": {str(k): v for k, v in table.items()},
                                                   "provenance": export.provenance(tf, a.seed)})
    print(f"{a.out}  {len(masks)} tiles")


def cmd_wfc(a):
    sample = Sprite.load(a.sample)
    w, h = (int(x) for x in a.size.lower().split("x"))
    from .rng import master_seed, sha256
    seed16 = master_seed(sha256(bytes(sample.px)).hex(), a.seed, 0)
    res = wfc.generate(sample, w, h, seed16, a.n, a.attempts)
    res.sprite.save(a.out, a.scale)
    print(f"{a.out}  {w}x{h}  patterns {res.patterns}  attempts {res.attempts}" + ("  FALLBACK (sample tiled)" if res.fallback else ""))


def cmd_uikit(a):
    tf = typefile.load(a.type)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    k = uikit.build_kit(tf, a.seed)
    k["atlas"].save(out / "atlas.png")
    k["panels"]["normal"].save(out / "panel.png")
    (out / "kit.json").write_text(uikit.kit_json(k["kit"]), encoding="utf-8")
    (out / "panel_normal.tres").write_text(uikit.godot_stylebox(k["kit"], "atlas.png"), encoding="utf-8")
    (out / "panel.css").write_text(uikit.css_border_image(k["kit"], "panel.png"), encoding="utf-8")
    uikit.nine_slice(k["panels"]["normal"], uikit.insets(tf.data), 64, 32).save(out / "preview.png", 4)
    print(f"{out}/  atlas.png kit.json panel_normal.tres panel.css preview.png")


def cmd_validate(a):
    bad = 0
    files = []
    for p in a.paths:
        p = Path(p)
        files += typefile.type_files(p) if p.is_dir() else [p]
    for f in files:
        try:
            tf = typefile.load(f)
            print(f"ok    {f}  {tf.id}  {tf.type_hash[:12]}")
        except typefile.TypeFileError as e:
            bad += 1
            print(f"FAIL  {f}")
            for prob in e.problems:
                print(f"      - {prob}")
    if not files:
        print("no type files found")
        return 1
    return 1 if bad else 0


def cmd_share(a):
    if a.decode:
        info = sharecode.decode(a.decode)
        for root in typefile.search_path():
            for f in typefile.type_files(root) if root.exists() else []:
                try:
                    tf = typefile.load(f)
                except typefile.TypeFileError:
                    continue
                if tf.type_hash.startswith(info["type_hash_prefix"]):
                    print(json.dumps({**info, "type_id": tf.id}))
                    if a.out:
                        gen.sprite(tf, info["seed"]).save(a.out, a.scale)
                    return 0
        print(json.dumps(info))
        print("no local type file matches this code's type hash", file=sys.stderr)
        return 1
    tf = typefile.load(a.type)
    print(sharecode.encode(tf.type_hash, a.seed))


def cmd_brood(a):
    tf = typefile.load(a.type)
    frames, inherited = brood.breed(tf, a.parent_a, a.parent_b, a.child)
    trio = [gen.sprite(tf, a.parent_a), frames[0], gen.sprite(tf, a.parent_b)]
    export.contact_sheet(trio, 3, 2).save(a.out, a.scale)
    print(f"{a.out}  parent A | child | parent B")
    print(json.dumps(inherited, indent=2))


def cmd_verdict(a):
    tf = typefile.load(a.type)
    s = gen.sprite(tf, a.seed)
    print(json.dumps({"spec": verdicts.spec_verdict(tf, s), "target": verdicts.target_verdict(s, a.target)}, indent=2))


def cmd_ascii(a):
    tf = typefile.load(a.type)
    s = gen.sprite(tf, a.seed)
    Path(a.out).write_text(export.ascii_export(s, f"{tf.id} seed {a.seed}", export.provenance(tf, a.seed)), encoding="utf-8")
    print(a.out)


def cmd_list(a):
    for root in typefile.search_path():
        for f in typefile.type_files(root) if root.exists() else []:
            try:
                tf = typefile.load(f)
                print(f"{tf.id:34} {tf.generator:9} {tf.data['tag']:34} {tf.license}")
            except typefile.TypeFileError as e:
                print(f"{f}: INVALID ({len(e.problems)} problems)")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="pixelgoblin", description=f"PixelGoblin {VERSION} — {CREDIT}")
    ap.add_argument("--version", action="version", version=f"PixelGoblin {VERSION}\n{CREDIT}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, helptext):
        p = sub.add_parser(name, help=helptext, description=helptext, epilog=f"example:\n  {EXAMPLES[name]}",
                           formatter_class=argparse.RawDescriptionHelpFormatter)
        p.set_defaults(fn=fn)
        return p

    def common(p, out=True, seed=True):
        if seed:
            p.add_argument("--seed", type=int, default=0, help="whole number; same seed = same sprite")
        if out:
            p.add_argument("--out", required=True, help="output file")
            p.add_argument("--scale", type=int, default=1, help="upscale the saved PNG (pixels stay square)")

    p = add("gen", cmd_gen, "Generate one sprite from a type file and a seed.")
    p.add_argument("type", help="type file path or id")
    common(p)
    p.add_argument("--name", help="a name instead of a seed")
    p.add_argument("--sub", help="variant overlay, like snow")
    p.add_argument("--tier", type=int, choices=[8, 16, 32, 64, 128, 256], help="rig tier")
    p.add_argument("--era", help="rig era: 8-bit, 16-bit, 32-bit, hd")
    p.add_argument("--rim", action="store_true", help="light rim outline")
    p = add("sheet", cmd_sheet, "Generate many seeds as one contact sheet, to review variety.")
    p.add_argument("type")
    p.add_argument("--seeds", default="0-31", help="like 0-63 or 1,5,9")
    p.add_argument("--cols", type=int, default=8)
    common(p, seed=False)
    p = add("anim", cmd_anim, "Export an animation strip + Aseprite-style JSON, with the flash-hazard check.")
    p.add_argument("type")
    common(p)
    p = add("convert", cmd_convert, "Turn an image into pixel art using a tag's profile.")
    p.add_argument("image")
    p.add_argument("--tag", required=True, help="like creature.small or env (see types/tags.toml)")
    p.add_argument("--set", action="append", help="override a profile value, like --set colors=6")
    common(p, seed=False)
    p = add("likeness", cmd_likeness, "Learn a type file from one example image, to generate more like it.")
    p.add_argument("image")
    p.add_argument("--tag", required=True)
    p.add_argument("--id", required=True, help="id for the new type, like my.creature.frog")
    p.add_argument("--out", required=True, help="output .toml")
    p = add("autotile", cmd_autotile, "Build a 47-tile blob autotile set from a terrain type file.")
    p.add_argument("type")
    common(p)
    p = add("wfc", cmd_wfc, "Grow a seamless texture from a small sample (Wave Function Collapse).")
    p.add_argument("sample")
    p.add_argument("--size", default="32x32")
    p.add_argument("--n", type=int, default=2, help="pattern size: 2 is robust at any size; 3 keeps more structure but falls back above ~32px until backtracking lands (P2)")
    p.add_argument("--attempts", type=int, default=8)
    common(p)
    p = add("uikit", cmd_uikit, "Build a UI kit (9-slice panels, button states, icons) for games and apps.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True, help="output folder")
    p = add("validate", cmd_validate, "Check type files and explain every problem in plain English.")
    p.add_argument("paths", nargs="+")
    p = add("share", cmd_share, "Make a share code for a sprite, or turn a code back into the sprite.")
    p.add_argument("type", nargs="?")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--decode")
    p.add_argument("--out")
    p.add_argument("--scale", type=int, default=1)
    p = add("brood", cmd_brood, "Breed two seeds of one type into a child that inherits from both.")
    p.add_argument("type")
    p.add_argument("parent_a", type=int)
    p.add_argument("parent_b", type=int)
    p.add_argument("--child", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    p = add("verdict", cmd_verdict, "Two separate verdicts: does it match its type file, and does it fit a target platform.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--target", default="modern", choices=sorted(verdicts.TARGETS))
    p = add("ascii", cmd_ascii, "Longevity export: the sprite as plain text anyone can read without software.")
    p.add_argument("type")
    common(p)
    add("list", cmd_list, "List every type file on the search path.")

    def rigopts(p):
        p.add_argument("--name", help="a name instead of a seed: the same name is always the same character")
        p.add_argument("--sub", help="variant overlay, like snow or cave (or a full type id)")
        p.add_argument("--tier", type=int, choices=list(rig.TIERS), help="rig tier (8 to 256 px)")
        p.add_argument("--era", choices=sorted(rig.ERAS), help="era palette rule, like 8-bit or 16-bit")
        p.add_argument("--rim", action="store_true", help="light rim instead of dark outline (for dark backgrounds)")
        p.add_argument("--team", help="clan colours, like ashfang (see *.teams.toml)")

    p = add("card", cmd_card, "Character card: one character at every tier, with era, colours and what each tier adds.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("chain", cmd_chain, "Export the build chain: one PNG per tier plus chain.json for engines.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True, help="output folder")
    rigopts(p)
    p = add("roster", cmd_roster, "Every rig type in a folder, one character each, on one sheet.")
    p.add_argument("folder")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--tier", type=int, default=64, choices=list(rig.TIERS))
    p.add_argument("--era", choices=sorted(rig.ERAS))
    p.add_argument("--sub")
    p.add_argument("--cols", type=int, default=9)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    p = add("gif", cmd_gif, "Animated GIF (idle or walk for characters), with the flash-hazard check.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--anim", default="idle", choices=sorted(rig.POSES))
    p.add_argument("--ms", type=int, default=160)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("squint", cmd_squint, "Readability at 1x: edge contrast on four backgrounds, detail and mass.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    rigopts(p)
    p = add("family", cmd_family, "Three generations: four founders, two children, one grandchild.")
    p.add_argument("type")
    p.add_argument("founders", type=int, nargs=4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    p = add("watch", cmd_watch, "Dropzone: convert every image that arrives with a .tag file beside it.")
    p.add_argument("folder")
    p.add_argument("--once", action="store_true", help="scan once and exit (otherwise keep watching)")
    p.add_argument("--every", type=int, default=5, help="seconds between scans")
    p.add_argument("--scale", type=int, default=1)
    from .gen import rig3d
    p = add("view", cmd_view, "One character (or beast) from any direction: side, back, isometric, top-down or free rotation.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--view", default="iso_sw", choices=list(rig3d.VIEWS))
    p.add_argument("--yaw", type=int, help="free rotation: 0 front, 90 facing left, 180 back, 270 facing right")
    p.add_argument("--pitch", type=int, help="tilt: 0 level, 30 isometric, 90 straight down")
    p.add_argument("--anim", choices=["idle", "walk_side"], help="write a GIF of this motion instead of a still")
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("turnaround", cmd_turnaround, "Eight directions (every 45 degrees) on one sheet, for 8-way sprites.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--pitch", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("expressions", cmd_expressions, "Expression sheet: the same face with every expression.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("clans", cmd_clans, "The same character in every clan's colours.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("zoom", cmd_zoom, "Animated zoom from a crowd-sized sprite to the portrait, dissolving between chain tiers.")
    p.add_argument("type")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--from", dest="from_tier", type=int, default=16, choices=list(rig.TIERS))
    p.add_argument("--to", dest="to_tier", type=int, default=256, choices=list(rig.TIERS))
    p.add_argument("--steps", type=int, default=24)
    p.add_argument("--ms", type=int, default=80)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("ride", cmd_ride, "A rider on a mount, from any direction, at the mount's scale.")
    p.add_argument("type", help="the rider's type")
    p.add_argument("mount", help="the mount's type, like boc.mount.boar")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mount-seed", type=int, default=0)
    p.add_argument("--view", default="side_right", choices=list(rig3d.VIEWS))
    p.add_argument("--yaw", type=int)
    p.add_argument("--pitch", type=int)
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    rigopts(p)
    p = add("city", cmd_city, "A whole population from a list of names: census, households and the village with them in it.")
    p.add_argument("city", help="city file or id, like boc.city.goblintown")
    p.add_argument("names", help="text file, one citizen per line")
    p.add_argument("--seed", type=int, default=1, help="village seed")
    p.add_argument("--tier", type=int, default=32, choices=list(rig.TIERS), help="size of the household sheet")
    p.add_argument("--out", required=True, help="output folder")
    add("packs", cmd_packs, "List the resource packs: what each holds, where it came from, how many colours were inferred.")
    p = add("pack", cmd_pack, "Every type in one resource pack on one sheet (races and traits are shown on a job).")
    p.add_argument("pack", help="pack id like boc.pack.ores, or its folder name like ores")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--role", default="boc.goblin.guard", help="the job that shows races and traits")
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=2)
    p = add("avatar", cmd_avatar, "A named soul's avatar (souls.toml): seeded from the soul name, offered as a supplement, never an overwrite.")
    p.add_argument("soul", help="a soul name from any souls.toml (like Aelren), or any name")
    p.add_argument("--role", help="job to draw them as (default: the soul's own, else father)")
    p.add_argument("--sub", help="race or overlay (default: the soul's own)")
    p.add_argument("--view", default="front", choices=list(rig3d.VIEWS))
    p.add_argument("--tier", type=int, default=64, choices=list(rig.TIERS))
    p.add_argument("--out", required=True)
    p.add_argument("--scale", type=int, default=1)
    p = add("sandbox", cmd_sandbox, "Goblin Grounds: a sandbox world from a biome's resource packs, with material weights, for games.")
    p.add_argument("--biome", default="forest", help="forest, mountain, coast, swamp, plain, desert, tundra, badlands, underwater")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--size", default="28x18", help="tiles, like 28x18")
    p.add_argument("--out", required=True, help="output folder: world.json, atlas.png, map.png")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rc = args.fn(args)
    except (typefile.TypeFileError, ValueError, FileNotFoundError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return rc or 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):  # a pipe on Windows defaults to cp1252; write UTF-8 everywhere
        _s.reconfigure(encoding="utf-8")
    sys.exit(main())


def cmd_card(a):
    tf = _load(a)
    seed = _seed(a)
    eras = {t: a.era for t in rig.TIERS} if a.era else None
    img, data = cards.card(tf, seed, eras=eras, title=a.name.upper() if a.name else None)
    img.save(a.out, a.scale)
    _write_json(Path(a.out).with_suffix(".json"), data)
    print(f"{a.out}  build chain {' '.join(str(r['tier']) for r in data['chain'])}  share {data['share']}")


def cmd_chain(a):
    tf = _load(a)
    seed = _seed(a)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    eras = {t: a.era for t in rig.TIERS} if a.era else None
    g, ch = rig.chain(tf, seed, eras=eras)
    rows = []
    for c in ch:
        name = f"{c['tier']}px_{c['era']}.png"
        c["sprite"].save(out / name)
        rows.append({"tier": c["tier"], "era": c["era"], "file": name, "colors": c["colors"], "features": c["features"]})
    _write_json(out / "chain.json", {"id": tf.id, "seed": seed, "genome": g, "chain": rows,
                                     "provenance": export.provenance(tf, seed)})
    print(f"{out}/  {len(rows)} tiers + chain.json")


def cmd_roster(a):
    files = typefile.type_files(Path(a.folder))
    sprites = []
    for f in files:
        tf = typefile.load(f) if not a.sub else typefile.compose(str(f), a.sub)
        if tf.generator != "rig":
            continue
        g = rig.genome(tf.data, rig.streams_for(tf, a.seed))
        sprites.append(rig.render(tf.data, g, a.tier, a.era)[0])
    if not sprites:
        print("no rig type files in that folder")
        return 1
    export.contact_sheet(sprites, a.cols, 2).save(a.out, a.scale)
    print(f"{a.out}  {len(sprites)} characters at {a.tier}px")


def cmd_gif(a):
    tf = _load(a)
    seed = _seed(a)
    if tf.generator == "rig":
        frames = rig.generate_frames(tf, seed, tier=a.tier or tf.data.get("tier", 64), era=a.era, anim=a.anim)
        ms = a.ms
    else:
        frames = gen.frames(tf, seed)
        ms = tf.data.get("animation", {}).get("frame_ms", a.ms)
    found = hazard.flash_check(frames, ms)
    _say_findings(found)
    gif.write(a.out, frames, ms, a.scale)
    print(f"{a.out}  {len(frames)} frames @ {ms} ms" + ("  (hazard reported)" if found else ""))


def cmd_squint(a):
    tf = _load(a)
    seed = _seed(a)
    if tf.generator == "rig":
        g = rig.genome(tf.data, rig.streams_for(tf, seed))
        s = rig.render(tf.data, g, a.tier or 32, a.era, rim=a.rim)[0]
    else:
        s = gen.sprite(tf, seed)
    print(json.dumps(readability.squint(s), indent=2))


def cmd_family(a):
    tf = _load(a)
    fam = brood.family(tf, tuple(a.founders), a.seed)
    row = lambda ids, over=None: [gen.frames(tf, i, over)[0] for i in ids]
    founders = row(fam["founders"])
    kids = [gen.frames(tf, c["seed"], c["overrides"])[0] for c in fam["children"]]
    grand = gen.frames(tf, fam["grandchild"]["seed"], fam["grandchild"]["overrides"])[0]
    blank = founders[0].copy()
    blank.px[:] = bytes(len(blank.px))
    sheet = export.contact_sheet(founders + [blank, kids[0], blank, kids[1]] + [blank, blank, grand, blank], 4, 3)
    sheet.save(a.out, a.scale)
    _write_json(Path(a.out).with_suffix(".json"), {k: v for k, v in fam.items()} | {
        "children": [{k: v for k, v in c.items() if k != "overrides"} for c in fam["children"]],
        "grandchild": {k: v for k, v in fam["grandchild"].items() if k != "overrides"}})
    print(f"{a.out}  row 1 founders · row 2 their children · row 3 the grandchild")


def cmd_watch(a):
    """Dropzone: any image with a sibling .tag file converts on arrival."""
    import time
    from .convert import convert_file
    root = Path(a.folder)
    out = root / "out"
    out.mkdir(parents=True, exist_ok=True)
    index_path = out / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    while True:
        done = 0
        for img in sorted(root.glob("*.png")):
            tag_file = img.with_suffix(".tag")
            if not tag_file.exists():
                continue
            key = f"{img.name}:{img.stat().st_size}:{tag_file.read_text(encoding='utf-8').strip()}"
            if index.get(img.name) == key:
                continue
            tag = tag_file.read_text(encoding="utf-8").strip()
            try:
                s, rep = convert_file(img, tag)
                s.save(out / img.name, a.scale)
                _write_json(out / (img.stem + ".json"), export.provenance(None, None, source=img.name, conversion=rep))
                index[img.name] = key
                done += 1
                print(f"converted {img.name} as {tag}")
            except (ValueError, typefile.TypeFileError) as e:
                print(f"skipped {img.name}: {e}")
        index_path.write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")
        if a.once:
            print(f"{done} new")
            return 0
        time.sleep(a.every)


def cmd_view(a):
    from .gen import beast, rig3d
    tf = _load(a)
    seed = _seed(a)
    tier = a.tier or tf.data.get("tier", 64)
    poses = rig3d_poses(a.anim)
    if tf.generator == "beast":
        bg = beast.genome(tf.data, beast.streams_for(tf, seed))
        frames = [beast.render(tf.data, bg, tier, a.view, a.yaw, a.pitch, a.era, p, a.rim) for p in poses]
    else:
        g = rig.genome(tf.data, rig.streams_for(tf, seed))
        frames = [rig3d.render_view(tf.data, g, tier, a.view, a.yaw, a.pitch, a.era, p, a.rim) for p in poses]
    if a.anim:
        gif.write(a.out, frames, 160, a.scale)
    else:
        frames[0].save(a.out, a.scale)
    print(f"{a.out}  {frames[0].w}x{frames[0].h}  {len(frames)} frame(s)  view {a.view if a.yaw is None and a.pitch is None else f'yaw {a.yaw} pitch {a.pitch}'}")


def rig3d_poses(anim):
    if anim == "walk_side":
        return [{"stride": 2}, {"bob": 1}, {"stride": -2}, {"bob": 1}]
    if anim == "idle":
        return rig.POSES["idle"]
    return [{}]


def cmd_turnaround(a):
    from .gen import rig3d
    tf = _load(a)
    seed = _seed(a)
    tier = a.tier or 64
    g = rig.genome(tf.data, rig.streams_for(tf, seed))
    items = [(f"{y} deg", rig3d.render_view(tf.data, g, tier, yaw=y, pitch=a.pitch, era=a.era, rim=a.rim)) for y in rig3d.TURNAROUND]
    sheet = export.contact_sheet([s for _, s in items], 8, 0)
    sheet.save(a.out, a.scale)
    _write_json(Path(a.out).with_suffix(".json"), {"id": tf.id, "seed": seed, "tier": tier, "pitch": a.pitch,
                                                   "frames": [{"yaw": y, "x": i * sheet.w // 8, "w": items[i][1].w, "h": items[i][1].h} for i, y in enumerate(rig3d.TURNAROUND)]})
    print(f"{a.out}  8 directions at {tier}px, tilt {a.pitch}")


def cmd_expressions(a):
    tf = _load(a)
    t = a.tier or 128
    cards.labelled(cards.expressions(tf, _seed(a), t, a.era), t, 9).save(a.out, a.scale)
    print(f"{a.out}  {len(rig.EXPRESSIONS)} expressions at {t}px")


def cmd_clans(a):
    tf = _load(a)
    t = a.tier or 64
    items = cards.team_row(tf, _seed(a), t, a.era)
    cards.labelled(items, t, len(items)).save(a.out, a.scale)
    print(f"{a.out}  {len(items) - 1} clans")


def cmd_zoom(a):
    tf = _load(a)
    frames = cards.zoom(tf, _seed(a), a.from_tier, a.to_tier, a.steps)
    gif.write(a.out, frames, a.ms, a.scale)
    print(f"{a.out}  {len(frames)} frames, {a.from_tier} px to {a.to_tier} px")


def cmd_ride(a):
    from .gen import beast
    rider = _load(a)
    mount = typefile.load(a.mount)
    s = beast.mounted(rider, _seed(a), mount, a.mount_seed, a.tier or 128, a.view, a.yaw, a.pitch, a.era, None, a.rim)
    s.save(a.out, a.scale)
    print(f"{a.out}  {s.w}x{s.h}  rider on {mount.id}")


def cmd_city(a):
    from . import city
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cty = city.load_city(a.city)
    people = city.census(cty, city.parse_names(Path(a.names).read_text(encoding="utf-8")))
    city.village(cty, people, a.seed).save(out / "village.png")
    houses = {}
    for p in people:
        houses.setdefault(p["household"], []).append(p)
    items = []
    for h, members in houses.items():
        for p in members:
            items.append((p["name"].split(" ")[0] + "\n" + p["role"].split(".")[-1].replace("_", " "), city.sprite(p, a.tier)))
    cards.labelled(items, a.tier, 10, 2).save(out / "citizens.png", 2)
    _write_json(out / "census.json", {"city": cty["id"], "citizens": city.public(people)})
    print(f"{out}/  {len(people)} citizens in {len(houses)} households: census.json, citizens.png, village.png")


def cmd_packs(a):
    for p in typefile.packs():
        c = p.get("counts", {})
        src = p.get("source", {})
        print(f"{p['id']:24} {c.get('types', 0):4} types  {c.get('inferred_colors', 0):3} with inferred colours  from {src.get('skill', '?')}  {p['label']}")


def _pack(name: str) -> dict:
    for p in typefile.packs():
        if p["id"] == name or p["id"] == f"boc.pack.{name}" or Path(p["path"]).parent.name == name:
            return p
    raise ValueError(f"no pack called {name!r}; run `pixelgoblin packs`")


def cmd_pack(a):
    p = _pack(a.pack)
    items = []
    for tid in p.get("types", []):
        if ".sub." in tid:
            tf = typefile.compose(a.role, tid)
            g = rig.genome(tf.data, rig.streams_for(tf, a.seed))
            s = rig.render(tf.data, g, 64)[0]
        else:
            tf = typefile.load(tid)
            if tf.generator == "autotile":
                s = autotile.build_tileset(tf, a.seed)[0]
            elif tf.generator == "uikit":
                k = uikit.build_kit(tf, a.seed)
                s = uikit.nine_slice(k["panels"]["normal"], uikit.insets(tf.data), 48, 24)
            else:
                s = gen.frames(tf, a.seed)[0]
        items.append((tf.data.get("label", tid.split(".")[-1])[:12] if ".sub." not in tid else typefile.load(tid).data.get("label", tid)[:12], s))
    if not items:
        raise ValueError(f"{p['id']} holds data only ({', '.join(p.get('data', []))}); nothing to draw")
    cell = max(max(s.w, s.h) for _, s in items)
    cell = min(cell, 160)
    pages = cards.labelled_pages(items, cell, max(1, min(12, 960 // (cell + 6))))
    outs = [Path(a.out)] + [Path(a.out).with_name(f"{Path(a.out).stem}-{k + 2}{Path(a.out).suffix}") for k in range(len(pages) - 1)]
    for sheet, o in zip(pages, outs):
        sheet.save(o, a.scale)
    print(f"{a.out}  {len(items)} from {p['id']}" + (f" on {len(pages)} sheets ({', '.join(o.name for o in outs[1:])} too: one palette holds 256 colours)" if len(pages) > 1 else ""))


def cmd_avatar(a):
    from .gen import rig3d
    souls = {}
    for root in typefile.search_path():
        for f in Path(root).rglob("souls.toml"):
            for e in typefile._read_toml(f).get("entities", []):
                souls[e["name"].lower()] = e
                souls[e["id"].lower()] = e
    e = souls.get(a.soul.lower(), {})
    role = a.role or e.get("role", "boc.goblin.father")
    sub = a.sub or e.get("sub")
    tf = typefile.compose(role, sub) if sub else typefile.load(role)
    soul = e.get("soul_name", a.soul)
    seed = seed_from_name("soul:" + soul)
    g = rig.genome(tf.data, rig.streams_for(tf, seed))
    rig3d.render_view(tf.data, g, a.tier, a.view).save(a.out, a.scale)
    _write_json(Path(a.out).with_suffix(".json"), {"soul_name": soul, "seed": str(seed), "role": role, "sub": sub, "known_soul": bool(e),
                                                   "supplement": True, "overwrites": None,
                                                   "rule": "supplement-but-never-overwrite: an offered appearance; it replaces no identity and writes nothing into the soul's own records"})
    print(f"{a.out}  avatar for {soul!r} ({'known soul' if e else 'any name'}), as {role.split('.')[-1]}" + (f" {sub.split('.')[-1]}" if sub else ""))


def cmd_sandbox(a):
    from . import sandbox
    w, h = (int(v) for v in a.size.lower().split("x"))
    if not (12 <= w <= 64 and 10 <= h <= 48):
        raise ValueError("--size must be between 12x10 and 64x48 tiles")
    plan = sandbox.world(a.biome, a.seed, w, h)
    paths = sandbox.export(plan, Path(a.out))
    q = ", ".join(f"{x['count']} {typefile.load(x['type']).data.get('label', x['type'])}" for x in plan["quests"])
    print(f"{a.out}  {a.biome} {w}x{h}: {len(plan['things'])} things, quests: {q or 'none'}  ({', '.join(p.name for p in paths)})")
