#!/usr/bin/env python3
"""Make the session-3 images for the build record, with the engine alone.

usage: record_gallery.py OUT_DIR

Every picture is a pure function of committed type files and the seeds
below, so anyone can regenerate the record's gallery and get the same bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pixelgoblin import brood, cards, export, font, gen, typefile  # noqa: E402
from pixelgoblin.gen import rig  # noqa: E402
from pixelgoblin.rng import seed_from_name  # noqa: E402
from pixelgoblin.sprite import TRANSPARENT, Sprite, blit  # noqa: E402

BG, INK, MUTE = (236, 230, 212, 255), (38, 38, 30, 255), (106, 101, 82, 255)
ROLES = ROOT / "flavors" / "boc" / "village" / "roles"


def labelled(items: list[tuple[str, Sprite]], cell: int, cols: int, label_rows: int = 1) -> Sprite:
    """Sprites bottom-aligned in equal cells, each with a caption underneath."""
    lab_h = 7 * label_rows + 3
    rows = (len(items) + cols - 1) // cols
    W, H = cols * (cell + 6) + 6, rows * (cell + lab_h + 6) + 6
    out = Sprite(W, H, [TRANSPARENT, BG, INK, MUTE])
    out.px[:] = bytes([1]) * (W * H)
    for i, (label, s) in enumerate(items):
        x0, y0 = 6 + (i % cols) * (cell + 6), 6 + (i // cols) * (cell + lab_h + 6)
        blit(out, s, x0 + (cell - s.w) // 2, y0 + cell - s.h)
        for k, line in enumerate(label.split("\n")[:label_rows]):
            while font.text_width(line) > cell and len(line) > 1:
                line = line[:-1]
            font.draw(out, x0 + (cell - font.text_width(line)) // 2, y0 + cell + 3 + 7 * k, line, 2 if k == 0 else 3)
    return out


def role_ids() -> list[str]:
    return [typefile.load(p).id for p in typefile.type_files(ROLES)]


def draw(tf, seed: int, tier: int, era=None, rim=False) -> Sprite:
    g = rig.genome(tf.data, rig.streams_for(tf, seed))
    return rig.render(tf.data, g, tier, era, rim=rim)[0]


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    ids = role_ids()
    label = lambda tf: tf.data.get("label", tf.id.split(".")[-1])
    # the roster at 64 px and at 16 px (the same seed: the same goblins)
    labelled([(label(typefile.load(i)), draw(typefile.load(i), 7, 64)) for i in ids], 64, 9).save(out / "roster64.png", 2)
    labelled([(label(typefile.load(i)), draw(typefile.load(i), 7, 16).scaled(3)) for i in ids], 48, 9).save(out / "roster16.png", 2)
    # one hunter, every subspecies
    subs = sorted(typefile.load(p).id for p in typefile.type_files(ROOT / "flavors" / "boc" / "village" / "subspecies"))
    row = [("role as written", draw(typefile.load("boc.goblin.hunter"), 11, 64))]
    row += [(typefile.load(s).data.get("label", s).replace(" Goblin", ""), draw(typefile.compose("boc.goblin.hunter", s), 11, 64)) for s in subs]
    labelled(row, 64, 6).save(out / "subspecies.png", 2)
    # one goblin in four eras at 64 px
    smith = typefile.load("boc.goblin.blacksmith")
    grub = seed_from_name("Grubnak")
    labelled([(f"{e} {rig.ERAS[e]['max_colors']} COL", draw(smith, grub, 64, e)) for e in rig.ERAS], 64, 4).save(out / "eras.png", 3)
    # build bit chains as character cards
    for name, rid, seed in (("card_grubnak", "boc.goblin.blacksmith", grub), ("card_chief", "boc.goblin.village_chief", 3),
                            ("card_shaman", "boc.goblin.shaman", 5)):
        tf = typefile.load(rid)
        spr, _ = cards.card(tf, seed, title="Grubnak" if name == "card_grubnak" else None)
        spr.save(out / f"{name}.png", 1)
    # the rim, for dark ground
    ass = typefile.load("boc.goblin.assassin")
    dark = Sprite(1, 1, [TRANSPARENT, (24, 22, 26, 255)])
    pair = [("no rim", draw(ass, 0, 64)), ("with rim", draw(ass, 0, 64, rim=True))]
    sheet = labelled(pair, 64, 2)
    di = sheet.color_index(dark.palette[1])
    for i in range(len(sheet.px)):
        if sheet.px[i] == 1:
            sheet.px[i] = di
    sheet.palette[2] = (233, 227, 207, 255)
    sheet.save(out / "rim.png", 3)
    # the goblins from before the references, now with two legs
    old = typefile.load("boc.creature.goblin")
    export.contact_sheet([gen.sprite(old, s) for s in range(16)], 8, 2).save(out / "goblins2.png", 4)
    # villages
    for name, sid, seed, sc in (("village", "boc.scene.village", 1, 3), ("village_hd", "boc.scene.village.hd", 1, 2)):
        gen.frames(typefile.load(sid), seed)[0].save(out / f"{name}.png", sc)
    # a family, three generations
    hunter = typefile.load("boc.goblin.hunter")
    fam = brood.family(hunter, (21, 22, 23, 24), 1)
    f = lambda s, o=None: gen.frames(hunter, s, o)[0]
    blank = Sprite(64, 64, [TRANSPARENT])
    tree = [(f"founder {c}", f(s)) for c, s in zip("ABCD", fam["founders"])]
    tree += [("", blank), ("child of A+B", f(fam["children"][0]["seed"], fam["children"][0]["overrides"])), ("", blank),
             ("child of C+D", f(fam["children"][1]["seed"], fam["children"][1]["overrides"]))]
    tree += [("", blank), ("", blank), ("grandchild", f(fam["grandchild"]["seed"], fam["grandchild"]["overrides"])), ("", blank)]
    labelled(tree, 64, 4).save(out / "family.png", 2)
    # a Warren dungeon
    gen.frames(typefile.load("vanilla.warren.crypt"), 3)[0].save(out / "warren.png", 2)
    print(f"{out}  {len(list(out.glob('*.png')))} images")
    return 0




def session4(out: Path) -> None:
    """Views, mounts, clans, expressions, zoom, the city, props, icons."""
    from pixelgoblin import cards, city
    from pixelgoblin.gen import beast, rig3d
    out.mkdir(parents=True, exist_ok=True)
    names = ["front", "side_right", "back", "side_left", "iso_sw", "iso_se", "iso_ne", "iso_nw", "three_quarter", "top"]
    items = []
    for rid, seed in (("guard", 0), ("shaman", 1), ("scout", 0), ("chiefs_consort", 0), ("miner", 1)):
        tf = typefile.load("boc.goblin." + rid)
        g = rig.genome(tf.data, rig.streams_for(tf, seed))
        for v in names:
            items.append((v.replace("_", " ") if rid == "guard" else "", rig3d.render_view(tf.data, g, 64, v)))
    cards.labelled(items, 92, 10).save(out / "views.png", 2)
    smith = typefile.load("boc.goblin.blacksmith")
    grub = seed_from_name("Grubnak")
    g = rig.genome(smith.data, rig.streams_for(smith, grub))
    rig3d.render_view(smith.data, g, 256, "iso_sw").save(out / "iso256.png", 1)
    labelled([(f"{y} deg", rig3d.render_view(smith.data, g, 64, yaw=y, pitch=30)) for y in rig3d.TURNAROUND], 92, 8).save(out / "turnaround.png", 2)
    walk = [rig3d.render_view(smith.data, g, 64, "side_right", pose=p) for p in ({"stride": 2}, {"bob": 1}, {"stride": -2}, {"bob": 1})]
    labelled([(f"walk {i + 1}", s) for i, s in enumerate(walk)], 64, 4).save(out / "walkside.png", 3)
    boar, wolf, rider = typefile.load("boc.mount.boar"), typefile.load("boc.mount.wolf"), typefile.load("boc.goblin.rider")
    mitems = []
    for tf in (boar, wolf):
        bg = beast.genome(tf.data, beast.streams_for(tf, 1))
        for v in ("side_right", "iso_sw", "front"):
            mitems.append((tf.data["label"] + " " + v.replace("_", " "), beast.render(tf.data, bg, 128, v)))
    for tf, v in ((boar, "side_right"), (boar, "iso_sw"), (wolf, "side_left"), (wolf, "iso_ne")):
        mitems.append(("rider " + v.replace("_", " "), beast.mounted(rider, 2, tf, 1, 128, v)))
    labelled(mitems, 136, 5).save(out / "mounts.png", 1)
    mus = typefile.load("boc.goblin.musician")
    cards.labelled(cards.expressions(mus, 4, 128), 128, 9).save(out / "expressions.png", 1)
    hunter = typefile.load("boc.goblin.hunter")
    row = cards.team_row(hunter, 2, 64)
    cards.labelled(row, 64, len(row)).save(out / "clans.png", 2)
    zf = cards.zoom(typefile.load("boc.goblin.shaman"), 5, 16, 256, 24)
    labelled([(f"{k + 1}", zf[k]) for k in (0, 3, 6, 9, 12, 15, 18, 23)], 256, 8).save(out / "zoom.png", 1)
    cty = city.load_city("boc.city.goblintown")
    people = city.census(cty, city.parse_names((ROOT / "flavors" / "boc" / "village" / "goblintown.names.txt").read_text()))
    city.village(cty, people, 1).save(out / "town.png", 3)
    houses = {}
    for p in people:
        houses.setdefault(p["household"], []).append(p)
    fam = []
    for h in ("Ashfang", "Reedwhistle", "Stonejaw", "Deepdelve"):
        for p in houses[h]:
            fam.append((p["name"].split(" ")[0] + ("\nchild" if p["parents"] else "\n" + p["role"].split(".")[-1].replace("_", " ")), city.sprite(p, 64)))
    labelled(fam, 64, 7, 2).save(out / "households.png", 2)
    from pixelgoblin import gen as G
    G.frames(typefile.load("boc.scene.village.hd"), 1)[0].save(out / "village_hd4.png", 1)
    ids = role_ids()
    labelled([(typefile.load(i).data.get("label", "")[:9], draw(typefile.load(i), 7, 8).scaled(4)) for i in ids], 32, 15).save(out / "icons8.png", 3)
    mi, fi = typefile.load("boc.goblin.miner"), typefile.load("boc.goblin.fisher")
    labelled([("miner", draw(mi, 1, 128)), ("fisher", draw(fi, 1, 128))], 128, 2).save(out / "dataitems.png", 1)
    print(f"{out}  session 4 images")


def session5(out: Path) -> None:
    """Resource packs, folk and traits, Goblin Grounds."""
    from pixelgoblin import cards, sandbox
    from pixelgoblin.gen import rig3d
    from pixelgoblin.tiles import autotile
    out.mkdir(parents=True, exist_ok=True)
    packs = {p["id"]: p for p in typefile.packs()}
    folk = []
    for rid in packs["boc.pack.races"]["types"]:
        tf = typefile.compose("boc.goblin.guard", rid)
        g = rig.genome(tf.data, rig.streams_for(tf, 3))
        folk.append((typefile.load(rid).data["label"][:11], rig.render(tf.data, g, 64)[0]))
    cards.labelled(folk, 64, 10).save(out / "folk.png", 2)
    stacks = []
    for name, sub, role in (("Thrain", "dwarf,axis_flame", "blacksmith"), ("Aelwyn", "elf,axis_frost", "hunter"), ("Ushra", "orc,axis_ferocity", "warrior_heavy"),
                            ("Pip", "halfling", "cook"), ("Nerissa", "merfolk,axis_water", "fisher"), ("Vex", "drow,axis_shadow", "assassin")):
        tf = typefile.compose(f"boc.goblin.{role}", sub)
        g = rig.genome(tf.data, rig.streams_for(tf, seed_from_name(name)))
        stacks.append((f"{name}", rig3d.render_view(tf.data, g, 64, "iso_sw")))
    labelled(stacks, 92, 6).save(out / "stacks.png", 2)
    for pid, fname, cell, cols, sc in (("boc.pack.flora", "flora", 48, 15, 2), ("boc.pack.fauna", "fauna", 32, 14, 3), ("boc.pack.ores", "ores", 16, 20, 4)):
        items = [(typefile.load(t).data.get("label", "")[:9], gen.frames(typefile.load(t), 1)[0]) for t in packs[pid]["types"]]
        for k, sheet in enumerate(cards.labelled_pages(items, cell, cols)):
            sheet.save(out / f"{fname}{'' if k == 0 else k + 1}.png", sc)
    skies = [t for t in packs["boc.pack.biomes"]["types"] if t.endswith(".sky")]
    labelled([(typefile.load(t).data["label"][:14], gen.frames(typefile.load(t), 1)[0]) for t in skies], 160, 3).save(out / "biomes.png", 1)
    sandbox.render(sandbox.world("mountain", 3)).save(out / "grounds_map.png", 2)
    print(f"{out}  session 5 images")


if __name__ == "__main__":
    if "--session5" in sys.argv:
        session5(Path(sys.argv[1]))
        sys.exit(0)
    if "--session4" in sys.argv:
        session4(Path(sys.argv[1]))
        sys.exit(0)
    sys.exit(main())
