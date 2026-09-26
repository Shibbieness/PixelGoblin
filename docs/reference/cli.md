# CLI reference

Generated from the parser by `tests/gate.py --regen-docs`. Do not edit by hand;
gate B14 fails if this page and the program disagree.

## `gen`

Generate one sprite from a type file and a seed.

```
pixelgoblin gen types/vanilla/creature.blob.toml --seed 42 --out blob.png --scale 4
```

- `type` — type file path or id
- `--seed` — whole number; same seed = same sprite
- `--out` — output file
- `--scale` — upscale the saved PNG (pixels stay square)
- `--name` — a name instead of a seed
- `--sub` — variant overlay, like snow
- `--tier` — rig tier
- `--era` — rig era: 8-bit, 16-bit, 32-bit, hd
- `--rim` — light rim outline

## `sheet`

Generate many seeds as one contact sheet, to review variety.

```
pixelgoblin sheet vanilla.creature.blob --seeds 0-63 --out blobs.png --scale 3
```

- `type`
- `--seeds` — like 0-63 or 1,5,9
- `--cols`
- `--out` — output file
- `--scale` — upscale the saved PNG (pixels stay square)

## `anim`

Export an animation strip + Aseprite-style JSON, with the flash-hazard check.

```
pixelgoblin anim vanilla.creature.blob --seed 7 --out blob_idle.png
```

- `type`
- `--seed` — whole number; same seed = same sprite
- `--out` — output file
- `--scale` — upscale the saved PNG (pixels stay square)

## `convert`

Turn an image into pixel art using a tag's profile.

```
pixelgoblin convert photo.png --tag creature.small --out small.png --scale 4
```

- `image`
- `--tag` — like creature.small or env (see types/tags.toml)
- `--set` — override a profile value, like --set colors=6
- `--out` — output file
- `--scale` — upscale the saved PNG (pixels stay square)

## `likeness`

Learn a type file from one example image, to generate more like it.

```
pixelgoblin likeness frog.png --tag creature.small --id my.creature.frog --out frog.toml
```

- `image`
- `--tag`
- `--id` — id for the new type, like my.creature.frog
- `--out` — output .toml

## `autotile`

Build a 47-tile blob autotile set from a terrain type file.

```
pixelgoblin autotile vanilla.terrain.grass --seed 1 --out grass_tiles.png
```

- `type`
- `--seed` — whole number; same seed = same sprite
- `--out` — output file
- `--scale` — upscale the saved PNG (pixels stay square)

## `wfc`

Grow a seamless texture from a small sample (Wave Function Collapse).

```
pixelgoblin wfc sample.png --size 48x48 --seed 3 --out floor.png
```

- `sample`
- `--size`
- `--n` — pattern size: 2 is robust at any size; 3 keeps more structure but falls back above ~32px until backtracking lands (P2)
- `--attempts`
- `--seed` — whole number; same seed = same sprite
- `--out` — output file
- `--scale` — upscale the saved PNG (pixels stay square)

## `uikit`

Build a UI kit (9-slice panels, button states, icons) for games and apps.

```
pixelgoblin uikit vanilla.ui.stone --seed 1 --out kit/
```

- `type`
- `--seed`
- `--out` — output folder

## `validate`

Check type files and explain every problem in plain English.

```
pixelgoblin validate types/ flavors/
```

- `paths`

## `share`

Make a share code for a sprite, or turn a code back into the sprite.

```
pixelgoblin share vanilla.creature.blob --seed 42      |   pixelgoblin share --decode PG-...
```

- `type`
- `--seed`
- `--decode`
- `--out`
- `--scale`

## `brood`

Breed two seeds of one type into a child that inherits from both.

```
pixelgoblin brood vanilla.creature.blob 11 29 --child 5 --out kid.png --scale 4
```

- `type`
- `parent_a`
- `parent_b`
- `--child`
- `--out`
- `--scale`

## `verdict`

Two separate verdicts: does it match its type file, and does it fit a target platform.

```
pixelgoblin verdict vanilla.creature.blob --seed 42 --target nes
```

- `type`
- `--seed`
- `--target`

## `ascii`

Longevity export: the sprite as plain text anyone can read without software.

```
pixelgoblin ascii vanilla.creature.blob --seed 42 --out blob.txt
```

- `type`
- `--seed` — whole number; same seed = same sprite
- `--out` — output file
- `--scale` — upscale the saved PNG (pixels stay square)

## `list`

List every type file on the search path.

```
pixelgoblin list
```


## `card`

Character card: one character at every tier, with era, colours and what each tier adds.

```
pixelgoblin card boc.goblin.village_chief --name Grubnak --out chief_card.png
```

- `type`
- `--seed`
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `chain`

Export the build chain: one PNG per tier plus chain.json for engines.

```
pixelgoblin chain boc.goblin.blacksmith --seed 3 --out smith/   (+ --sub snow, --era 8-bit)
```

- `type`
- `--seed`
- `--out` — output folder
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `roster`

Every rig type in a folder, one character each, on one sheet.

```
pixelgoblin roster flavors/boc/village/roles --tier 64 --seed 1 --out roster.png --sub cave
```

- `folder`
- `--seed`
- `--tier`
- `--era`
- `--sub`
- `--cols`
- `--out`
- `--scale`

## `gif`

Animated GIF (idle or walk for characters), with the flash-hazard check.

```
pixelgoblin gif boc.goblin.musician --seed 2 --anim walk --tier 64 --out walk.gif --scale 2
```

- `type`
- `--seed`
- `--anim`
- `--ms`
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `squint`

Readability at 1x: edge contrast on four backgrounds, detail and mass.

```
pixelgoblin squint boc.goblin.assassin --seed 1 --tier 32
```

- `type`
- `--seed`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `family`

Three generations: four founders, two children, one grandchild.

```
pixelgoblin family vanilla.creature.blob 11 29 40 57 --out family.png --scale 4
```

- `type`
- `founders`
- `--seed`
- `--out`
- `--scale`

## `watch`

Dropzone: convert every image that arrives with a .tag file beside it.

```
pixelgoblin watch ./dropzone --once     (frog.png + frog.tag containing creature.small)
```

- `folder`
- `--once` — scan once and exit (otherwise keep watching)
- `--every` — seconds between scans
- `--scale`

## `view`

One character (or beast) from any direction: side, back, isometric, top-down or free rotation.

```
pixelgoblin view boc.goblin.guard --name Brakka --view iso_sw --tier 64 --out brakka_iso.png --scale 4   (or --yaw 120 --pitch 20)
```

- `type`
- `--seed`
- `--view`
- `--yaw` — free rotation: 0 front, 90 facing left, 180 back, 270 facing right
- `--pitch` — tilt: 0 level, 30 isometric, 90 straight down
- `--anim` — write a GIF of this motion instead of a still
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `turnaround`

Eight directions (every 45 degrees) on one sheet, for 8-way sprites.

```
pixelgoblin turnaround boc.goblin.scout --seed 3 --pitch 30 --tier 64 --out scout_8dir.png --scale 2
```

- `type`
- `--seed`
- `--pitch`
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `expressions`

Expression sheet: the same face with every expression.

```
pixelgoblin expressions boc.goblin.musician --seed 4 --tier 128 --out faces.png
```

- `type`
- `--seed`
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `clans`

The same character in every clan's colours.

```
pixelgoblin clans boc.goblin.guard --seed 2 --out clans.png --scale 2
```

- `type`
- `--seed`
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `zoom`

Animated zoom from a crowd-sized sprite to the portrait, dissolving between chain tiers.

```
pixelgoblin zoom boc.goblin.shaman --seed 5 --from 16 --to 256 --out zoom.gif
```

- `type`
- `--seed`
- `--from`
- `--to`
- `--steps`
- `--ms`
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `ride`

A rider on a mount, from any direction, at the mount's scale.

```
pixelgoblin ride boc.goblin.rider boc.mount.boar --seed 2 --mount-seed 1 --view side_right --tier 128 --out rider.png --scale 2
```

- `type` — the rider's type
- `mount` — the mount's type, like boc.mount.boar
- `--seed`
- `--mount-seed`
- `--view`
- `--yaw`
- `--pitch`
- `--out`
- `--scale`
- `--name` — a name instead of a seed: the same name is always the same character
- `--sub` — variant overlay, like snow or cave (or a full type id)
- `--tier` — rig tier (8 to 256 px)
- `--era` — era palette rule, like 8-bit or 16-bit
- `--rim` — light rim instead of dark outline (for dark backgrounds)
- `--team` — clan colours, like ashfang (see *.teams.toml)

## `city`

A whole population from a list of names: census, households and the village with them in it.

```
pixelgoblin city boc.city.goblintown flavors/boc/village/goblintown.names.txt --out town/
```

- `city` — city file or id, like boc.city.goblintown
- `names` — text file, one citizen per line
- `--seed` — village seed
- `--tier` — size of the household sheet
- `--out` — output folder
