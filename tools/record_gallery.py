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


if __name__ == "__main__":
    sys.exit(main())
