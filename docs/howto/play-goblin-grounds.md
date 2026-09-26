# Play (and build with) Goblin Grounds

Goblin Grounds is the sandbox and minigame area: a small world made from a biome's resource packs, where your goblin walks, gathers and delivers to the forge. It is two things that agree exactly:

- `editor/pixelgoblin-grounds.html`: the playable page (one file, offline).
- `pixelgoblin sandbox`: the same world as files for a game engine.

## Play

1. Open the page. Pick a **biome** and a **world seed**. The same biome and seed always make the same world.
2. Pick your goblin: **name**, **job** and **folk** (any race from the races pack).
3. Walk with the arrow keys or WASD, or tap a tile to walk there. On a phone, use the arrow pad.
4. Things you can gather get a glowing edge when you stand next to them. Press **E** or **Space** to gather.
5. Watch your **pack**: ore weighs what CRUCIBLE says (a 500 cm³ chunk of iron is about 3.9 kg). A goblin carries 12 kg at full speed falling to half speed; you cannot lift past 18 kg.
6. Take the quest items to the **forge** and press E. Ore that no quest wants is smelted.
7. When every quest is done, the page tells you how many steps it took. Try the next seed.

## Build

Press **Build**, pick anything that lives in this biome, and click tiles to place it. Alt-click removes a thing. **Save world.json** keeps your world, edits included.

## Export for a game

```
pixelgoblin sandbox --biome mountain --seed 3 --size 28x18 --out grounds/
```

| File | What it is |
|---|---|
| `world.json` | tiles (0 ground, 1 water, 2 rock), things with positions and seeds, start, forge, quests, and for every sprite its atlas rectangle, weight in grams and where the weight came from |
| `atlas.png` | every sprite used, on one sheet |
| `map.png` | a preview of the whole world |

## What is guaranteed

Gate B23 checks, in every biome and two seeds each:

- everything gatherable can be reached from the start (a walled-off control proves the check can fail);
- no quest asks for more than the world holds, and no two things share a tile;
- speed falls from 100% to 50% as the pack fills, and no further;
- the page plans exactly the engine's world, including with a 64-bit seed.

## How it is built

`pixelgoblin/sandbox.py` holds the world planner (`plan_world`, `reachable`, `quests`, `speed`) in the transpiler's integer subset. `tools/transpile_rig.py` turns it into JavaScript, so the page and the command line cannot disagree. The page adds walking, gathering, the forge and building; the engine owns the world.

—Shibbieness
—Claude
