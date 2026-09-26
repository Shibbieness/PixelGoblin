# The tier chain: one character at 8, 16, 32, 64, 128 and 256 px

This page explains how PixelGoblin keeps a character recognisably *that character* from a tiny 8 px sprite up to a 256 px portrait, what each tier is allowed to draw, and what "8-bit", "16-bit" and so on mean here. The **build bit chain** of a character is that character drawn at every tier, side by side. It is the reference an artist or a game uses to keep the tiers consistent. You can see one in the workbench (Characters tab), or print one with `pixelgoblin card` and `pixelgoblin chain`.

## First, what "bit" means (and what it does not)

"8-bit", "16-bit" and so on name console generations: the width of the CPU's registers. They were never sprite sizes. An NES game (8-bit CPU) drew 8×8 and 16×16 sprites. A Super Nintendo game (16-bit CPU) drew anything from 8×8 to 64×64. So "a 32-bit character" does not describe a size. It describes a *look*: how many colours per sprite, how the shading is banded, what the outline does.

PixelGoblin therefore keeps two separate settings, and never merges them:

- the **tier** is the pixel resolution: 8, 16, 32, 64, 128 or 256 pixels square;
- the **era** is the look: the palette budget, shading bands, outline style and dithering of a console generation.

The request was for 8, 16, 32, 64, 128 and 256 "bit". Resolutions of 8 to 256 px are exactly the tiers. For looks, the 128-bit and 256-bit console generations (Dreamcast, PS2 onward) had no distinct pixel-art style of their own; their 2D art is what we now call **HD pixel art**. So there are four eras: `8-bit`, `16-bit`, `32-bit` and `hd`. Any era can be applied at any tier. An 8-bit-look 64 px sprite is allowed, and it is a real choice people make.

## The one rule that makes it work: genome vs render

A character has two halves:

| Half | What it holds | Does it look at the tier? |
|---|---|---|
| **Genome** | Height, head size and width, ear length, lift and width, nose, eyes and iris, expression, hair and colour, outfit and cloth colours, headwear, held items, back item, accessories. Each concern draws from its own named random stream (`g/body`, `g/face`, `g/hair`, `g/outfit`, `g/headwear`, `g/items`, `g/accessories`). | **Never** |
| **Render** | Which features exist at this size (the LOD ladder), how many shade bands, the era's colour budget, outline width, dither, and the small-tier stylisation. | Yes, and only this half |

Because the genome never sees the tier, the 8 px goblin and the 256 px goblin are the same data drawn twice. Nothing about the character can drift between tiers, because there is only one of it.

All geometry lives in a 1024×1024 design space and is drawn with integer tests only (ellipses, rounded rectangles, capsules, triangles, ring segments), sampled at pixel centres. Every tier divides 1024, so pixel centres land on whole design units. There is no floating point anywhere, so the JavaScript workbench draws the same pixels as Python, which gate B13 checks at every tier.

## Per-tier specification

| Tier | Design units per pixel | Shade bands (max) | Default era | Head bonus | Eye bonus | Outline | Extras |
|---|---|---|---|---|---|---|---|
| 8 px | 128 | 1 (flat) | 8-bit | +14 points | 0 | none (the silhouette is the outline) | feet drawn in front of held items |
| 16 px | 64 | 2 | 16-bit | +8 points | +40% | 1 px dark | feet drawn in front of held items |
| 32 px | 32 | 3 | 16-bit | +4 points | +25% | 1 px selective (coloured per material) | contact shadows |
| 64 px | 16 | 4 | 32-bit | +1 point | +10% | 1 px selective | contact shadows |
| 128 px | 8 | 5 | hd | 0 | 0 | 1 px selective | contact shadows, ordered dither |
| 256 px | 4 | 5 | hd | 0 | 0 | 2 px (selective, then dark) | contact shadows, ordered dither |

The **head and eye bonuses** are the chibi rule that every hand-made sprite chain uses. Small sprites have bigger heads and eyes because identity lives in the face. They are added in the render and never stored in the genome.

**Snapped features** (ears, staffs, spears, straps, glasses, horns) never get thinner than one pixel, so a goblin keeps its ears at 8 px.

**The leg gap never closes.** Leg spacing grows to leave at least one pixel of clear space at every tier. Gate B16 checks every role at 8, 16, 32 and 64 px, drawing the legs twice. Drawn alone, there must be exactly two. Drawn fully dressed, items may hide one leg but must never add one. The old goblin template with a merged centre column (the "three legs" bug) fails this check, and a control in the gate proves it.

## Eras

| Era | Colours per sprite (plus transparent) | Shade bands | Outline | Dither | Modelled on |
|---|---|---|---|---|---|
| `8-bit` | 3 | 2 | plain dark, locked through reduction | no | NES-class: 3 colours + transparent per sprite |
| `16-bit` | 15 | 3 | selective | no | SNES/Genesis-class: 15 + transparent per sprite palette |
| `32-bit` | 31 | 4 | selective | no | GBA/PS1-class 2D: larger palettes, smoother ramps |
| `hd` | 255 | 5 | selective | yes, at 128 px and up | modern HD pixel art |

When a render has more colours than its era allows, colours are merged deterministically, integers only. The cheapest pair always merges first, where cost is weighted RGB distance times the smaller pixel count, and the more-used colour survives. For the 8-bit era the darkest colour is locked so the outline survives. Gate B16 checks the budget at every tier of the default chain and with an era forced.

## The level-of-detail ladder

Each feature has the smallest tier at which it is drawn. Below that tier it is left out, not smeared. This table is `LOD` in `pixelgoblin/gen/rig.py`, and gate B16 checks that every feature the geometry emits has a rung.

| From | Features |
|---|---|
| 8 px | body, head, ears, legs, feet, arms, torso, top, bottom, hair, large held items, large headwear, large back items |
| 16 px | eyes, held items, headwear, back items, beard, belt, glasses, goggles, pauldrons, fins |
| 32 px | mouth, nose, hands, sleeves, scarf, earrings, buckle |
| 64 px | brows, eye whites, inner ears, necklace, tusks, pouches, bracers, tongue, flowers, straps |
| 128 px | pupils, highlights, pattern, stitches, fur tufts, nails |

Feet were on the 32 px rung until session 3. At 8 px that left guards and warriors with no feet, because a spear and a shield covered both legs. Feet are now on the 8 px rung, and below 32 px they are drawn in front of everything, even a role's signature item.

**Signatures (session 4).** Each role has one feature that says who it is: what it holds, else its headwear, its back item, a beard or its top, or whatever `[role] signature` names. That feature is promoted to the 8 px rung, snapped to a whole pixel and drawn on top below 32 px, and its colours are the last to merge in a small palette. Gate B20 checks that no two roles share an 8 px icon.

**8-bit eyes (session 4).** At three colours, eyes and mouths are drawn in the outline colour, as NES sprites did, so a face survives the palette.

## How identity across tiers is measured

`rig.coherence(data, genome, tier)` compares a tier with a 256 px reference drawn with **the same stylisation and the same feature set**, then reduced to the small grid by majority vote. Whatever differs after that is pure rasterisation loss. The function reports two integers:

- **IoU**: silhouette overlap, as a percentage;
- **material**: of the pixels both drawings fill, the share with the same material (skin, cloth, metal and so on).

These values were measured over all 30 goblin role and base types at seed 0 (session 4, with signatures):

| Tier | IoU average | IoU minimum | Material average | Material minimum |
|---|---|---|---|---|
| 8 px | 59 | 35 | 81 | 37 |
| 16 px | 79 | 67 | 81 | 60 |
| 32 px | 92 | 82 | 93 | 81 |
| 64 px | 96 | 91 | 96 | 85 |
| 128 px | 96 | 95 | 96 | 95 |

The 8 px material average fell from 86 to 81 when signatures arrived. That is expected: a signature item is snapped to a whole pixel and drawn on top, which a 256 px reference can only partly reproduce. The icons became more distinct from each other (gate B20), and slightly less like a shrunken portrait.

Gate B16 holds floors just under these values. Read them honestly. At 32 px and above a character is very nearly the same drawing. At 16 px it is clearly the same character. At 8 px the materials still mostly agree (81% on average), but the outline is only about 60% the same, because in an 8×8 grid every snapped ear and every one-pixel foot is a big share of the picture. An 8 px sprite is an icon of the character, not a small copy of it, and that is true of hand-made sprite chains too.

## Transitions: moving between tiers

Some games switch tiers, for example a 16 px overworld sprite that becomes a 64 px battle sprite, or a crowd goblin that walks toward the camera. The chain makes this safe:

- **Colour identity is stable.** Every tier draws from the same material ramps, and the era only merges colours. A red cloak is red at every tier.
- **Proportions change smoothly.** The head bonus steps down 14 → 8 → 4 → 1 → 0 points, so adjacent tiers never differ by more than 6 points of head size.
- **Features only arrive; they do not move.** A feature appears at its rung and stays in the same place in design space at every larger tier. The workbench's "adds:" line under each tier lists what arrived.
- **Animation moves in whole pixels at every tier.** Poses offset by `px` (one pixel at the current tier), so a 4-frame idle bob is one pixel at 8 px and one pixel at 256 px, never a sub-pixel shimmer.

## Where the reference images come in

The roster (27 roles) and the village scene come from two reference images Mark supplied. They are kept out of the repository (`refs/` is git-ignored) and identified here by hash:

| Image | SHA-256 |
|---|---|
| `refs/roster.png` | `fa72b4544fa3ebd784c198a9fbf34be331d08aaa9a112232905099d95393a8ed` |
| `refs/village.png` | `772b1a8b3f1b048a2e2c2ca3bd4261d5669857919d39caf33fdd3a790c0d0ad9` |

`tools/extract_ramps.py` pulled the skin, leather, wood, brass, cloth and arcane ramps from them (OKLab hue windows, quantile bands). The metal ramp comes from CRUCIBLE. Grey cast iron's resistivity marks it as metallic, and that decides the shape of the ramp (a bright glint step). The base colour is authored, because CRUCIBLE holds no colour data. Each ramp's source is noted beside it in `flavors/boc/village/goblin.rig.toml`.

## Scenes: background characters are real characters

The village scene draws its crowd from the same rig at **depth tiers**: far goblins at 16 px, middle ones at 32 px and near ones at 64 px (32, 64 and 128 px in the HD village). So a background goblin keeps its ears, its eyes and its job. This answers "it could have better character quality in the background": the background characters are not smaller drawings, they are the same characters at a lower tier. In the workbench, clicking a goblin in the village opens it in Characters at every tier.

## Known limits

- The rider role has no mount yet. A mount is a second rig (a beast genome), and it belongs in its own type.
- Scene props (huts, stalls, trees) do not have tiers yet; only the characters do.
- 8 px identity is modest (see the measurements above). The honest improvement is hand-authored 8 px overrides per role, stored as data and checked against the chain.
- Coherence measures shape and material, not "does a person recognise this goblin". A person-rated check belongs with the playtest plan, not in a gate.

—Shibbieness
—Claude
