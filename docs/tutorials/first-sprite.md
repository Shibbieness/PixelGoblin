# Your first sprite

**Time:** about five minutes. **You need:** Python 3.11 or newer.

## 1. Make one sprite

```
python3 -m pixelgoblin gen vanilla.creature.blob --seed 42 --out blob.png --scale 6
```

Open `blob.png`. It is a small green, red or blue blob.

## 2. Make the same sprite again

Run the same command again. You get the same file, pixel for pixel. That is the main promise of PixelGoblin: the same type file and seed always make the same sprite.

## 3. See many at once

```
python3 -m pixelgoblin sheet vanilla.creature.blob --seeds 0-63 --out blobs.png --scale 3
```

Each seed is a different blob. The command also tells you how many are different from each other.

## 4. Get a share code

```
python3 -m pixelgoblin share vanilla.creature.blob --seed 42
```

The code (it starts with `PG-`) is the whole sprite in one line. Anyone with the same type file can turn it back:

```
python3 -m pixelgoblin share --decode PG-... --out same.png --scale 6
```

## 5. Try the editor

Open `editor/pixelgoblin.html`. Pick a type file, press **Roll 16**, and click any sprite. **Open in editor** lets you paint over it.

**Next:** `make-a-species.md`.

—Shibbieness
—Claude
