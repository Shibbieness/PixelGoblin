# Generate sprites inside a game

The point: ship **type files and seeds**, not thousands of PNGs. The game makes each sprite when it needs it.

## Python (Book of Cities, tools, servers)

```python
from pixelgoblin import typefile, gen

goblin = typefile.load("boc.creature.goblin")      # or a path
frames = gen.frames(goblin, seed=npc.id)           # list of Sprite
rgba = frames[0].rgba()                            # bytes, w*h*4
```

Cache by `(type_hash, seed)`. The same key always gives the same pixels, so a cache entry never goes stale.

## Browser, Electron, web games

`editor/pg-core.js` is the same engine in JavaScript. It produces **identical pixels**, and gate B13 checks this on every build.

```js
const frames = PG.frames(typeData, "12345");   // seed as string or BigInt for 64-bit
frames[0].px        // palette indices
frames[0].palette   // [[r,g,b,a], ...]
```

## Any host through Vanilla Core

PixelGoblin is a Vanilla Core flavor (`flavor.toml`):

```
vanilla-core run flavor.toml --capability generate --param type=vanilla.creature.blob --param seed=7
```

Images come back as base64 PNG in JSON.

## Godot, Unity and C

These are planned: the Rust core with a C ABI, a Godot extension and a C# wrapper. See `docs/explanation/gameplan.md`, phase P7. Until then, export sheets:

```
python3 -m pixelgoblin anim boc.creature.goblin --seed 7 --out goblin.png
```

This writes `goblin.png` and `goblin.json` (Aseprite-style frames and tags). Godot, Phaser and Unity importers read that layout.

## Budgets

Measure on your own target. As a rough guide, the Python engine makes a 20x24 goblin in a few milliseconds. For a crowd, generate at load time and cache.

—Shibbieness
—Claude
