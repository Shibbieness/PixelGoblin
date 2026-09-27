# Use PixelGoblin from Claude

There are four ways to reach PixelGoblin from a chat with Claude. They share one engine, so the same name makes the same goblin in all of them.

| Way | Best for | What you get |
|---|---|---|
| **PixelGoblin Pocket** (a web page) | Making a goblin quickly by hand | Type a name, pick a job, folk, trait, clan, mount, size and era, drag to turn it, save a picture or 8 directions, copy a share code |
| **Goblin Grounds** (a web page) | Playing with the packs | Walk a goblin through a biome, gather weighed ore and fungi for the forge's quests, or build |
| **The pixelgoblin plugin** | Asking Claude for goblins in words | Three skills and nine tools that return pictures in the chat |
| **The PixelGoblin Workshop** (`pixelgoblin-workshop.skill`) | Working on PixelGoblin itself | The whole project, indexed and uploadable as a skill, with the original capsule kept inside it unchanged |

## The Pocket widget

`editor/pixelgoblin-pocket.html` is one file and works offline. Open it in a browser, or publish it as an artifact with the `downloads` capability so its save buttons work.

A **share code** looks like `pg2/blacksmith/dwarf/axis_flame/ashfang/boar/-/64/45/30/Thrain`: job, folk, trait, clan, mount, era, size, turn, tilt, name. Paste one and press Load to get the same goblin back. Older `pg1/` codes (no folk or trait) still load.

## The plugin

Build it with:

```
python3 tools/package.py plugin
```

This writes `dist/pixelgoblin.plugin`. Install it in Claude. It contains:

- **pixelgoblin** skill: makes goblins of every folk, views, sheets, GIFs, towns, pack sheets, avatars and sandbox worlds. The engine, the resource packs and all three web pages are inside it.
- **pixelgoblin-types** skill: helps write new jobs, clans, mounts and cities.
- **pixelgoblin-engine** skill: the rules for changing the engine.
- **pixelgoblin** MCP server (`server/pixelgoblin_mcp.py`, standard library only): nine tools.

| Tool | Does |
|---|---|
| `pixelgoblin_list` | lists jobs, clans, mounts, variants, cities, views, sizes and eras |
| `pixelgoblin_character` | one goblin, any view, turn and tilt, optionally riding or walking |
| `pixelgoblin_sheet` | card, turnaround, expressions, clans, zoom, chain or GIF |
| `pixelgoblin_city` | a town from a list of names |
| `pixelgoblin_pack` | every sprite in a resource pack |
| `pixelgoblin_avatar` | an Aether Library soul's avatar (a supplement, never an overwrite) |
| `pixelgoblin_sandbox` | a Goblin Grounds world: map, world.json, atlas |
| `pixelgoblin_cli` | any of the 32 commands |
| `pixelgoblin_selftest` | checks the engine and says where pictures are saved |

Pictures are saved in `~/PixelGoblin`, or in the folder named by `PIXELGOBLIN_OUT`. The server runs the engine in the same process and never prints anything but protocol messages, so its pictures are byte-identical to the command line's. Gate B21 checks that.

## The Workshop capsule (upload this one)

Build it with:

```
python3 tools/package.py workshop
```

This writes `dist/pixelgoblin-workshop.skill`: about 130 files, well under the 200-file limit for a skill upload. The whole repository is one file inside it, `build/source/pixelgoblin-src.zip`; the docs write a path inside that file as `src:path`. The pages, docs and codex stay loose so they can be read directly.

The helper `build/source/workshop.py` does the rest:

| Command | Does |
|---|---|
| `workshop.py unpack DIR` | makes a working copy you can run and change |
| `workshop.py original [PATH]` | lists or prints files of the original capsule |
| `workshop.py find WORDS` | searches the source and the original together |
| `workshop.py check` | confirms both match their fingerprints |

To improve PixelGoblin from a chat: unpack, change, run the gates, then `python3 tools/package.py workshop` in the copy makes the next version to upload. `codex/LINEAGE.md` inside the workshop says where everything from the original went.

The original capsule is frozen. The copy Mark was given is kept at `dist/archive/pixelgoblin-pseudoskill-v1u0p1.skill` and inside every workshop; the forge refuses to run if it has changed.

## The original PseudoSkill capsule (frozen)

Build it with:

```
python3 tools/package.py capsule
```

This writes `dist/pixelgoblin-pseudoskill.skill`, in the PseudoSkills Builder's capsule structure: `SKILL.md` (the router), `PseudoSKILL.md` (the full reference), `META.json`, `codex/` (index, narrative, changelog, tags, CALS namespace, open questions, one mini-index per module), `dependencies/`, `build/` (the whole runnable repository plus copies of the pages, docs, config and gallery), `pretune/` (twelve scenarios with expected pixel hashes) and `updates/` (eight empty slots for Companion Builder mode).

`tools/packaging_capsule.py validate <folder>` runs the Forge validation checklist. The capsule is never packaged if a check fails.

A skill upload accepts only one `SKILL.md`, so inside the capsule's `build/source/` the repository's own four skill files are renamed `<name>_SKILL.md` (for example `pixelgoblin_SKILL.md`). `build/source/packaging/RENAMED_SKILLS.md` lists them. If you copy `build/source/` out to build from it, run `python3 tools/packaging_capsule.py restore .` in the copy first.

—Shibbieness
—Claude
