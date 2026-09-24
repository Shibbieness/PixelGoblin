# Make a species

A species is one type file. This walks through `flavors/boc/goblin.species.toml`.

## 1. Copy a starting file

```
cp types/vanilla/creature.blob.toml my.creature.toml
```

Change `id` to something new, like `my.creature.imp`.

## 2. Draw the body template

The template is half the body when `mirror = true`. Each character is one cell:

| Character | Meaning |
|---|---|
| `.` | empty |
| `#` | always body |
| `1` | body or empty (random) |
| `2` | body or edge (random) |

The `1` and `2` cells are where variety comes from. Put them on the edges of the silhouette. Keep `#` in the middle.

## 3. Add colour ramps

Each ramp runs **dark to light**. The body uses one ramp, picked by `weight`. A ramp with `weight = 0` is only used by parts that name it.

## 4. Add parts

A part has its own template, anchor, `chance` (0 to 100) and optional `ramp`. Each part draws from **its own random stream**. Adding a part never changes the body of a creature you already liked.

## 5. Check it

```
python3 -m pixelgoblin validate my.creature.toml
```

Every problem comes back as a plain sentence, like "template (16x6 at [7, 0]) does not fit inside size 20x24 with a 1-pixel border for the outline".

## 6. Look at the variety

```
python3 -m pixelgoblin sheet my.creature.toml --seeds 0-63 --out imps.png --scale 3
```

Too similar? Add more `1` and `2` cells, or another ramp. Too noisy? Turn some `1` cells into `#`.

## 7. Make a variant

A variant file only says what is different:

```toml
extends = "my.creature.imp"
id = "my.creature.imp.frost"
```

Then list the ramps or parts to change. Tables merge. Lists (like `parts`) replace the parent's list.

## 8. Breed two you like

```
python3 -m pixelgoblin brood my.creature.toml 11 29 --child 5 --out kid.png --scale 5
```

The picture shows parent A, the child and parent B, and the command lists which parent each part came from.

—Shibbieness
—Claude
