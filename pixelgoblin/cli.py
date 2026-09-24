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

from . import CREDIT, VERSION, brood, export, gen, hazard, sharecode, typefile, uikit, verdicts
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


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _say_findings(findings) -> None:
    for f in findings:
        print(f"\n!! {f.kind} ({f.severity}, {f.status})\n   {f.mechanism}\n", file=sys.stderr)


def cmd_gen(a):
    tf = typefile.load(a.type)
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
    Path(a.out).write_text(text)
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
    (out / "kit.json").write_text(uikit.kit_json(k["kit"]))
    (out / "panel_normal.tres").write_text(uikit.godot_stylebox(k["kit"], "atlas.png"))
    (out / "panel.css").write_text(uikit.css_border_image(k["kit"], "panel.png"))
    uikit.nine_slice(k["panels"]["normal"], uikit.insets(tf.data), 64, 32).save(out / "preview.png", 4)
    print(f"{out}/  atlas.png kit.json panel_normal.tres panel.css preview.png")


def cmd_validate(a):
    bad = 0
    files = []
    for p in a.paths:
        p = Path(p)
        files += [f for f in sorted(p.rglob("*.toml")) if f.name != "tags.toml"] if p.is_dir() else [p]
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
            for f in sorted(root.rglob("*.toml")) if root.exists() else []:
                if f.name == "tags.toml":
                    continue
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
    Path(a.out).write_text(export.ascii_export(s, f"{tf.id} seed {a.seed}", export.provenance(tf, a.seed)))
    print(a.out)


def cmd_list(a):
    for root in typefile.search_path():
        for f in sorted(root.rglob("*.toml")) if root.exists() else []:
            if f.name == "tags.toml":
                continue
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
    p.add_argument("--n", type=int, default=3, help="pattern size (2 or 3)")
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
    sys.exit(main())
