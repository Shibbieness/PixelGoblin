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
- `--n` — pattern size (2 or 3)
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

