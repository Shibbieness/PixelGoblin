# Convert an image into pixel art

1. Pick a tag. Tags live in `types/tags.toml`. Examples: `creature`, `creature.small`, `object.icon`, `env`.
2. Run:
   ```
   python3 -m pixelgoblin convert frog.png --tag creature.small --out frog_px.png --scale 4
   ```
3. Change one setting for one run with `--set`:
   ```
   python3 -m pixelgoblin convert frog.png --tag creature.small --set colors=6 --set dither=bayer --out frog6.png
   ```

## What the tag decides

| Setting | Choices |
|---|---|
| `size` | longest side in pixels |
| `colors` | colour budget (always respected) |
| `outline` | `selout` (tinted), `dark`, `none` |
| `dither` | `none`, `bayer` (stable in animation), `fs` (stills only) |
| `downsample` | `mode` (flat art), `box` (photos), `median`, `nearest` |
| `palette` | `auto`, `pico8`, `gameboy`, `goblin16`, or a `.hex`/`.gpl` file |

A child tag like `creature.small` inherits from `creature` and changes only what it names.

## Make more things like it

```
python3 -m pixelgoblin likeness frog.png --tag creature.small --id my.creature.frog --out frog.toml
python3 -m pixelgoblin sheet frog.toml --seeds 0-31 --out frogs.png --scale 3
```

`likeness` learns the silhouette, its symmetry and its colour ramp. The edge cells become random, so each seed is a relative. It writes a normal type file, so you can edit it.

In the editor: **Convert**, choose a file, then **Learn likeness**.

## Input formats

PNG works with nothing installed. Other formats (JPEG, WebP) work if Pillow happens to be installed. The editor reads anything your browser can show.

—Shibbieness
—Claude
