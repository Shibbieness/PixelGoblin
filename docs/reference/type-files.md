# Type-file reference

Type files are TOML. Every field is a whole number, text, true/false, a list or a table. **Decimal numbers are refused**, so every platform generates the same pixels.

## Every type file

| Field | Required | Meaning |
|---|---|---|
| `schema` | yes | `"pixelgoblin/type@1"` |
| `id` | yes | dotted name, unique, no spaces |
| `tag` | yes | dotted tag; its root must be in `types/tags.toml` |
| `generator` | yes | `mask`, `lsystem`, `parallax`, `autotile`, `uikit`, `rig`, `beast`, `scene`, `warren` |
| `license` | yes | the licence of the **sprites** this file makes |
| `size` | yes | `[width, height]`, 4 to 512 (to 2048 for `scene` and `parallax`). For a `rig` it is the largest tier it may be drawn at; for a `warren` it is the map in tiles |
| `extends` | no | id of a parent type; tables merge, lists replace, and a key ending in `_add` (for example `accessories_add`) appends to the parent's list |

## `mask` — creatures, items, icons, fungi

| Field | Meaning |
|---|---|
| `mirror` | `true` makes the templates half-width and mirrors them |
| `outline_style` | `selout` (tinted by the body) or `plain` |
| `max_colors` | optional promise, checked by the spec verdict |
| `palette.outline` | outline colour |
| `[[palette.ramps]]` | `name`, `weight` (0 = only when named), `colors` (2 to 8, dark to light) |
| `[body]` | `template` (rows of `. 1 2 #`), `anchor` `[x, y]`, optional `ramp` |
| `[[parts]]` | `name` (unique), `chance` 0 to 100, `template`, `anchor`, optional `ramp` |
| `[features]` | `eyes` 0 to 2, `eye_color`, `eye_band` `[top%, bottom%]` of body height |
| `[animation]` | `frames` 1 to 8, `frame_ms` 16 to 2000 (bob and blink idle) |

A template plus its anchor must fit inside `size`, with a 1-pixel border for the outline.

## `lsystem` — trees, shrubs, coral, roots

`axiom`, `rules` (symbol to a list of `{to, weight}`), `iterations` 1 to 6, `step` `[min, max]`, `leaf_radius` 0 to 3, `fruit_chance`, `trunk_width` 1 or 2, `palette.bark`, `palette.leaf`, `palette.outline`, `palette.fruit`.

Symbols: `F` forward, `+` and `-` turn 45°, `[` push, `]` leaf then pop, `L` leaf.

## `parallax` — backdrops

`palette.sky` (top to bottom), `palette.star`, `stars`, and `[[layers]]` with `name`, `colors` (dark to light), `base` (% of height), `periods` and `amps` (one entry per noise octave), and `scroll` (%).

## `autotile` — terrain

`tile` 8 to 32, `palette.fill` (3 or more), `palette.outline`, `palette.highlight`.

## `uikit` — GUI slots

`tile`, `border` 1 to 3, `corner`, `icons` 0 to 16, `texture` (% speckle), `palette.material` (4 to 8), `palette.outline`.

## `rig` — characters drawn at 8 to 256 px

A rig type is usually three layers: a **species** file (the goblin), **role** files that `extends` it, and **subspecies** overlays applied with `typefile.compose(role, overlay)`. Only the overlay's own keys apply, so a snow goblin blacksmith keeps the blacksmith's outfit. How tiers and eras work is explained in `docs/explanation/tier-chain.md`.

| Field | Meaning |
|---|---|
| `tier` | the default tier for `gen` and `sheet`: one of 8, 16, 32, 64, 128, 256 |
| `label` | a display name, used on cards and in the workbench |
| `[species]` | ranges as `[low, high]` whole numbers: `head_adj`, `head_w`, `ear_len`, `ear_lift`, `ear_w`, `nose`, `eye`; lists: `iris`, `hair`, `hair_color`, `build`, `accessories` |
| `[role]` | lists to pick from: `age`, `build`, `top`, `bottom`, `cloth_a`, `cloth_b`, `hair`, `hair_color`, `headwear`, `held`, `offhand`, `back`, `expression`; `accessories` as `{ item, chance }` tables |
| `palette.outline`, `palette.rim` | the dark outline, and the light rim used with `--rim` |
| `[palette.materials]` | ramps (2 to 8 colours, dark to light) for `skin`, `leather`, `wood`, `metal`, `brass`, `paper`, `fur`, `glow`, `arcane`, `gem`, `eye_white`, `mouth`, `teeth` |
| `[palette.cloth]`, `[palette.hair]`, `[palette.iris]` | named ramps that `cloth_a`, `cloth_b`, `hair_color` and `iris` pick from |

Vocabulary (a misspelling is refused with a "did you mean"):

| Field | Allowed values |
|---|---|
| `age` | `child`, `teen`, `adult`, `elder` |
| `build` | `slim`, `average`, `stocky`, `heavy` |
| `hair` | `none`, `topknot`, `long`, `wild`, `braids`, `bun`, `mohawk`, `ponytail`, `twintails`, `short` |
| `top` | `none`, `tunic`, `vest`, `apron`, `robe`, `dress`, `armor_light`, `armor_heavy`, `wrap`, `cloak`, `fur_mantle`, `crop` |
| `bottom` | `none`, `trousers`, `shorts`, `skirt`, `kilt` |
| `headwear` | `none`, `hood`, `bandana`, `goggles`, `helm`, `feather_crown`, `chef_hat`, `horns`, `flower_crown`, `headscarf`, `cap`, `circlet` |
| `held`, `offhand` | `none`, `hammer`, `staff`, `book`, `bow`, `basket`, `spear`, `dagger`, `lute`, `lantern`, `ladle`, `brush`, `sword`, `wrench`, `mug`, `teddy`, `scroll`, `orb`, `map`, `bag`, `shield`, `whip`, `flask`, `axe` |
| `back` | `none`, `backpack`, `quiver`, `cape`, `big_pack`, `fur` |
| accessories | `beard`, `necklace`, `earrings`, `glasses`, `goggles`, `scarf`, `pauldrons`, `belt`, `pouches`, `bracers`, `tusks`, `fins`, `tattoo` |
| `expression` | `neutral`, `happy`, `curious`, `confident`, `thoughtful`, `annoyed`, `angry`, `surprised`, `playful` |

### Items written as data (`[items.<name>]`)

A rig type can add held items without code. Each item is a list of shapes in hundredths of the item scale (which follows head size), relative to the hand. x is mirrored for the left hand.

| Key | Meaning |
|---|---|
| `shape` | `E` ellipse `[cx, cy, rx, ry]`, `R` rounded box `[x0, y0, x1, y1, radius]`, `C` capsule `[x0, y0, x1, y1, r]`, `T` triangle `[x0, y0, x1, y1, x2, y2]`, `A` ring `[cx, cy, rx, ry, thickness, half]` |
| `at` | the numbers above, whole numbers |
| `mat` | a material: `wood`, `metal`, `cloth_a`, `leather`... |
| `layer` | stacks shapes (0 is the item's base) |
| `feat` | its rung on the LOD ladder: `held` (16 px) or `held.large` (8 px) |
| `snap` | `true` keeps it at least one pixel thick at every tier |

Name the item in `[role] held` or `offhand` like a built-in one. The miner's pickaxe and the fisher's rod are examples.

### Signatures

`[role] signature = "held"` (or `headwear`, `back`, `beard`, `top`) names the one feature drawn even at 8 px, snapped to a pixel and on top. Without it, the signature is the first of: held item, headwear, back item, beard, top. Its colours are also the last to merge in a small era palette.

## `beast` — mounts, built as solids

`[beast]`: `kind` (`boar` or `wolf`); ranges `length`, `height`, `girth`, `head`, `snout`, `ear`, `tail`; `tusk_chance` and `saddle_chance` (%); lists `coat` (from `palette.hair`), `iris` (from `palette.iris`), `blanket` (from `palette.cloth`). `palette.materials` needs `fur`, `skin`, `mouth`, `eye_white`, `teeth`, `hoof`, `leather` and `metal`. A beast is drawn in a cube twice the goblin's, so a rider fits on top at the same scale (`pixelgoblin ride`).

## Clans (`*.teams.toml`, schema `pixelgoblin/teams@1`)

`[teams.<name>]`: `label`, and `a` and `b` for the two cloth colours. Each is a name from `palette.cloth` or a new ramp of 2 to 8 colours. A clan changes only the clothes, after the character is decided, so the type hash and every random stream stay the role's own.

## Cities (`*.city.toml`, schema `pixelgoblin/city@1`)

`scene` (a scene id), `clans` (a list of team names), `[census]` (job weights for grown citizens), `[children]`, `[elders]`, `[subspecies]` and `[bands]` (weights). A names file beside it (`*.names.txt`) is the default population. See `docs/howto/build-a-city.md`.

## `scene` — a place with its people

`size` (up to 2048), counts `clouds`, `waterfalls`, `trees`, `huts`, `stalls`, and ramps `palette.sky`, `cloud`, `cliff_far`, `cliff`, `water`, `leaf`, `trunk`, `wood`, `roof`, `glow`, `ground`, plus `awnings` (a list of ramps).

Each `[[crowd]]` band has a `name`, a `tier` (the size its characters are drawn at), a `count`, `roles` (rig type ids; every role appears once before any repeats), `y` as `[top, bottom]` in % of scene height (where feet stand), optional `on = "platforms"`, and an optional `era`. A scene's seed stream is keyed to its own hash **and** the hashes of every role it uses, so editing a role file changes the village.

## `warren` — dungeons

`size` in tiles, `terrain` (an `autotile` type id), `rooms` and `room_size` as `[low, high]`, `attempts`, `loop_chance` (%), `corridor_width` 1 or 2, `kinds` (room labels cycled between the entrance and the boss room), `palette.void`, and `[palette.marks]` colours for `entrance`, `boss` and any kind. The room graph is built first and the tiles second, and every room is reachable from the entrance.

## Tags and profiles (`types/tags.toml`)

`[roots]` lists the allowed first segments. `[tag."a.b"]` tables are conversion profiles: `size`, `colors`, `outline`, `dither`, `downsample`, `palette`, `cleanup`. A misspelled root is refused with a "did you mean".

—Shibbieness
—Claude
