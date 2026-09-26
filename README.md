# PixelGoblin

**Scavenge an image. Grow a species. Ship it in a game.**

PixelGoblin makes pixel art three ways, all from one small engine:

1. **Generate.** A short text file (a *type file*) plus a number (a *seed*) makes a sprite. The same file and seed always make the same sprite, in the editor, in Python, and inside a game.
2. **Convert.** Give it any image and a tag like `creature.small`. It makes pixel art that fits that tag.
3. **Learn.** Give it one example. It writes a type file, which then makes more things like the example.

It also builds 47-tile autotile sets, seamless textures, parallax backdrops and UI kits (9-slice panels, button states, icons).

Characters are drawn from one genome at six resolutions (8, 16, 32, 64, 128 and 256 px), each with an era look (8-bit, 16-bit, 32-bit or HD), so a character's tiny sprite and its portrait are provably the same character. Every character can also be seen from the side, from behind, in isometric, from above or at any angle, because the front drawing is lifted into one 3D model that all the views come from. Riders sit on boars and wargs. Villages place real characters in the background, a list of names becomes a whole city of families, and Warren builds dungeons in which every room can be reached.

```
Built on PixelGoblin — © Shibbieness / M MAOU LLC
```

## Start in two minutes

Needs Python 3.11 or newer. Nothing to install.

```
python3 -m pixelgoblin sheet vanilla.creature.blob --seeds 0-31 --out blobs.png --scale 4
python3 -m pixelgoblin gen boc.creature.goblin --seed 7 --out goblin.png --scale 6
python3 -m pixelgoblin convert photo.png --tag creature.small --out small.png --scale 4
python3 -m pixelgoblin card boc.goblin.blacksmith --name Grubnak --out grubnak-card.png
python3 -m pixelgoblin gen boc.scene.village --seed 1 --out village.png --scale 3
python3 -m pixelgoblin view boc.goblin.guard --name Brakka --view iso_sw --out brakka.png --scale 4
python3 -m pixelgoblin city boc.city.goblintown flavors/boc/village/goblintown.names.txt --out town/
```

Or open `editor/pixelgoblin.html` in a browser. It is one file and works offline.

## Where to read next

| I want to… | Read |
|---|---|
| make my first sprite | `docs/tutorials/first-sprite.md` |
| design a whole species | `docs/tutorials/make-a-species.md` |
| turn an image into pixel art | `docs/howto/convert-an-image.md` |
| generate sprites inside a game | `docs/howto/use-in-a-game.md` |
| make a UI kit | `docs/howto/make-a-ui-kit.md` |
| draw one character at 8 to 256 px | `docs/explanation/tier-chain.md` |
| see a character from the side, behind, isometric or above | `docs/explanation/views.md` |
| build a city from a list of names | `docs/howto/build-a-city.md` |
| look up a command | `docs/reference/cli.md` |
| look up a type-file field | `docs/reference/type-files.md` |
| understand "same seed, same sprite" | `docs/explanation/determinism.md` |
| see how the build checks itself | `docs/explanation/gates.md` |
| see the road to the standalone product | `docs/explanation/gameplan.md` |
| see why things are the way they are | `docs/explanation/decisions.md` |

## Check the build

```
PYTHONHASHSEED=0 python3 tests/gate.py --all --report
PYTHONHASHSEED=0 python3 tests/gate.py --from-empty
```

`BUILD_STATUS.md` shows the last full run.

## Licence

- **Engine:** AGPL-3.0-or-later. It is free, and what you build on it stays free. A paid commercial licence is available for closed-source use (`LICENSE-COMMERCIAL.md`).
- **Sprites you make are yours.** The engine's licence does not cover its output.
- **The example type files** in `types/vanilla/` make CC0 sprites. You can use them for anything.
- `flavors/boc/` is Book of Cities flavour content, and it is not part of the vanilla pack.

See `NOTICE.md` and `ATTRIBUTION.md`.

—Shibbieness
—Claude
