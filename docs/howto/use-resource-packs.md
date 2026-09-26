# Use the resource packs

The resource packs turn Mark's world-building (the Book of Cities, its Compendium and the Aether Library) into type files PixelGoblin can draw right away, with CRUCIBLE's real material data where it applies. They live in `flavors/boc/packs/`, one folder per pack, each with a `pack.toml` manifest.

```
pixelgoblin packs                               # what is there, and where it came from
pixelgoblin pack ores --out ores.png --scale 3  # every sprite in a pack on one sheet
```

## The packs

| Pack | What it holds | Types |
|---|---|---|
| `races` | **Folk of the Book of Cities**: human, elf, dwarf, orc, goblin, halfling, gnome, tiefling, dungeon dweller, infernal, divine, and their variants (drow, duergar, merfolk, sea-elf, kuo-toa, tide-reader goblin and more) | 37 overlays |
| `biomes` | The nine biomes: a parallax sky and an autotile ground for each, plus which plants, fungi, animals and ores live there | 18 |
| `flora` | Trees, shrubs, flowers, grasses, reeds, vines, cacti, crops, and fungi | 100 |
| `fauna` | Animals and fish | 65 |
| `ores` | Ores, stones, gems and fantasy metals, each with its CRUCIBLE grounding | 60 |
| `compendium` | Rank badges (UI kits) and trait overlays from the Compendium, plus its catalog as data | 36 |
| `aether` | The Aether Library's named souls (avatar seeds), Brackrun-Hollow as a city, and its catalog | data |
| `world` | Crafting stations (five tiers) and districts, as data | data |

## Folk and traits are overlays

A folk is an overlay, like a goblin subspecies: it changes the body (stature, ears, nose, skin, eyes, hair, beards, tusks, fins), never the job. So any job can be any folk:

```
pixelgoblin view boc.goblin.blacksmith --name Thrain --sub dwarf --view iso_sw --out thrain.png --scale 3
```

Overlays **stack left to right**. A trait from the Compendium goes after a folk:

```
pixelgoblin card boc.goblin.hunter --name Aelwyn --sub elf,axis_frost --out aelwyn.png
```

Short names work (`dwarf`, `snow`, `axis_frost`); a misspelling is refused with a suggestion. In a city file, a `[subspecies]` key can be a full overlay id, so a city can hold mixed folk:

```toml
[subspecies]
"boc.race.sub.human" = 4
"boc.race.sub.halfling" = 1
common = 1
```

**Stature** is relative to goblin height and capped by the canvas: humans draw about 1.2 times a goblin (the Book of Cities ratio is about 1.4). Gate B22 checks that halflings and gnomes stay shorter than humans and orcs, and that every folk keeps two legs at every tier on two jobs.

## Ores are grounded in CRUCIBLE

Each ore has a `[crucible]` table:

| Field | Meaning |
|---|---|
| `grounding` | `grounded` (CRUCIBLE's density), `category_default` (CRUCIBLE has no number; a typical density for its kind), or `intentionally_ungrounded` (a fantasy material, which CRUCIBLE never fills from real data) |
| `density_kg_m3` | the density used |
| `chunk_grams` | what one gathered chunk (500 cm³) weighs |
| `crucible_ref`, `crucible_name`, `boc_bridge_id` | where the number came from |

Goblin Grounds uses `chunk_grams` for weight. Gate B22 checks every grounded density against CRUCIBLE's own number, and that no fantasy ore is ever passed off as grounded.

## Aether Library avatars

```
pixelgoblin avatar Aelren --view iso_sw --out aelren.png --scale 3
```

The avatar is seeded from the **soul name** (which survives reincarnation), drawn as the soul's listed job and folk, and written with a sidecar `.json` that says `"supplement": true` and `"overwrites": null`. This keeps the Aether Library's rule: a new appearance may be offered, never forced over an existing identity, and nothing is written into the Aether Library.

## Colours: stated or inferred

The source documents describe mechanics more than looks, so most colours are **inferred** from names ("rust red", "sea-green"). Every inferred entry says so in its `[provenance]` table, and each manifest counts them. When Mark decides a canonical palette, the source catalog changes and `tools/build_packs.py` regenerates the pack; gate B22 fails if the pack and its source disagree.

## Regenerating

```
python3 tools/build_packs.py          # write the packs from flavors/boc/packs/sources/
python3 tools/build_packs.py --check  # what gate B22 runs
```

The sources are JSON extracts of Mark's skills, kept in `flavors/boc/packs/sources/` with notes on what came from where. Never edit a generated pack file by hand.

—Shibbieness
—Claude
