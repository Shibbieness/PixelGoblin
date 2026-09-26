# PixelGoblin plugin

Make pixel-art goblins by asking for them.

Type or say a name, and you get the same goblin every time: at every size from 8 to 256 pixels, from the front, side, back, in isometric or from above. Make it a dwarf, an elf, an orc or any of 37 folk of the Book of Cities, add a Compendium trait, put it in clan colours, sit it on a war boar, make its eight directions for a game, or give it a list of names and get a whole town of families. Draw the Book of Cities' plants, animals and ores (weighed by CRUCIBLE), and play them in Goblin Grounds.

```
Built on PixelGoblin — © Shibbieness / M MAOU LLC
```

## What's inside

| Part | What it does |
|---|---|
| **pixelgoblin** skill | Makes goblins, views, sheets, GIFs and towns. The whole engine is inside it, so it works offline. |
| **pixelgoblin-types** skill | Helps you add new jobs, clans, mounts and cities (small text files). |
| **pixelgoblin-engine** skill | For working on PixelGoblin itself: the rules, the checks, where things are. |
| **pixelgoblin** tools (MCP) | Nine tools Claude can call directly: list, draw one goblin, make a sheet, build a city, show a resource pack, draw an Aether Library soul, build a Goblin Grounds world, run any command, and a self-test. They show the picture right in the chat. |
| Resource packs | Folk, biomes, plants, fungi, animals, fish and ores from the Book of Cities; ranks and traits from the Compendium; souls from the Aether Library. Inside the engine. |
| Three web pages | The **Pocket** (quick maker), **Goblin Grounds** (the sandbox game) and the full **Workbench**, in `skills/pixelgoblin/pages/`. Open any in a browser; they work offline. |

## Things to ask

- "Make a goblin called Grubnak, a blacksmith, from the side."
- "Show Mizzle the shaman in isometric, in Duskveil colours."
- "Make an 8-direction turnaround of Brakka the guard at 64 px."
- "Put a rider on a warg and show it from the back."
- "Here are 20 names. Build the town."
- "Make a character card for Tok, every size."
- "Turn this photo into 32 px pixel art."
- "Make Thrain, a dwarf blacksmith with the flame trait, from the side."
- "Show me every ore in the Book of Cities."
- "Draw Aelren from the Aether Library."
- "Build me a mountain world to play."

## Where pictures go

The tools save pictures in a folder called `PixelGoblin` in your home folder. To use another folder, set `PIXELGOBLIN_OUT` to it. If the home folder can't be written, they go to the system's temporary folder instead, and the tool says where.

## Needs

Python 3.11 or newer. Nothing else: the engine uses only Python's standard library.

## Licences

- The engine is **AGPL-3.0-or-later** (see `LICENSE`). A commercial licence that waives the share-alike condition is described in `LICENSE-COMMERCIAL.md`.
- Each picture carries the licence of the type file that made it. The vanilla pack is CC0-1.0. The goblin flavor (Book of Cities) is Proprietary, owned by Shibbieness / M MAOU LLC.
- Attribution: `ATTRIBUTION.md`.

—Shibbieness
—Claude
