---
name: pixelgoblin
description: This skill should be used when the user asks to "make a goblin", "draw a goblin called ...", "show my goblin from the side / back / isometric / top-down", "make a turnaround", "make a character card", "expression sheet", "put it in clan colours", "put it on a boar / wolf", "zoom from crowd to portrait", "build a city from these names", "make a dwarf / elf / orc blacksmith", "show the Book of Cities ores / plants / animals", "draw Aelren", "make a sandbox world", "play Goblin Grounds", "turn this picture into pixel art", "make a sprite sheet for my game", or mentions PixelGoblin, Grubnak, Goblintown, Brackrun-Hollow, resource packs, the workbench, the Pocket or Goblin Grounds. It makes deterministic pixel-art characters of every Book of Cities folk, views, sheets, whole towns, resource-pack sprites and sandbox worlds with the bundled PixelGoblin engine.
---

# PixelGoblin

PixelGoblin is Shibbieness's (Mark's) pixel-art generator. One name always makes the same goblin, at every size from 8 to 256 px, from any direction. It runs offline with the Python standard library only (Python 3.11 or newer).

The engine is bundled inside this skill folder, in `engine/`, with the resource packs (Book of Cities folk, biomes, plants, fungi, animals, ores grounded in CRUCIBLE; Compendium ranks and traits; Aether Library souls). Three ready-made web pages are in `pages/`: the workbench, the Pocket and Goblin Grounds.

## Talking to Mark

Mark has dyslexia. Keep replies short and plain. Use short sentences, simple words and clear headings. Show pictures instead of describing them. Name things by what they look like ("side view", "clan colours"), not by engine terms ("yaw 270", "with_team"), unless he uses the engine term first.

## Pick the route

Check in this order and use the first one that works.

1. **MCP tools present** (`pixelgoblin_character`, `pixelgoblin_sheet`, `pixelgoblin_city`, `pixelgoblin_pack`, `pixelgoblin_avatar`, `pixelgoblin_sandbox`, `pixelgoblin_list`, `pixelgoblin_cli`, `pixelgoblin_selftest`): call them. They return the picture inline and save it to the output folder (default `~/PixelGoblin`).
2. **A shell is available**: run the engine from this skill's `engine/` folder.
   ```bash
   ENGINE="<this skill's folder>/engine"   # the folder that holds this SKILL.md, plus /engine
   cd "$ENGINE" && python3 -m pixelgoblin view boc.goblin.blacksmith --name Grubnak --view iso_sw --out /tmp/grubnak.png --scale 3
   ```
   If the path is unknown, find it: `find / -path '*pixelgoblin/engine/pixelgoblin/cli.py' 2>/dev/null | head -1`.
   Write outputs to the working directory or outputs folder, then show them (send the file, or view it with Read).
3. **No shell, only artifacts**: publish `pages/pixelgoblin-pocket.html` (quick maker), `pages/pixelgoblin-grounds.html` (the sandbox minigame) or `pages/pixelgoblin.html` (full workbench) as an artifact, with the `downloads` capability so the Save buttons work. Mark's own published copies may already exist, all private to him: the Pocket at https://claude.ai/artifact/HRTVjLVPeRsQrRsMHbupqc, Goblin Grounds at https://claude.ai/artifact/UhFrDXaQNMqferxmQKQt1D and the workbench at https://claude.ai/artifact/EcDDXExxyk7zWFWsLFeZjS.

## The common jobs

| Mark asks for | Do this |
|---|---|
| A goblin called X | `view <role> --name X --view front` (or the character tool). Pick a role that fits; say which one. |
| From the side / back / isometric / top | `--view side_right`, `back`, `iso_sw`, `top`, `three_quarter`; free turn with `--yaw 0-359 --pitch 0-90` |
| Every size | `card <role> --name X` (8, 16, 32, 64, 128, 256 px in one picture) |
| Game-ready size chain | `chain <role> --name X --out folder/` (one PNG per size + chain.json) |
| 8 directions | `turnaround <role> --name X --pitch 30` |
| Faces | `expressions <role> --name X` |
| Clan colours | `--team ashfang` (7 clans: ashfang, cinderglass, duskveil, gildhand, mossback, skyrope, tidecaller); `clans` shows all |
| Riding | `ride <role> boc.mount.boar --name X --view side_right --tier 128` (or `boc.mount.wolf`) |
| Walking or idle GIF | `view ... --anim walk_side --out x.gif` or `gif <role> --anim walk` |
| Zoom crowd to portrait | `zoom <role> --name X --from 16 --to 256 --out zoom.gif` |
| A town from names | `city boc.city.goblintown names.txt --out town/` (one name per line; a surname that is a clan name joins that clan) |
| Snow, cave and other variants | `--sub snow` (see `list`) |
| Another folk (dwarf, elf, orc, halfling, merfolk, drow...) | `--sub dwarf` on any job: `view boc.goblin.blacksmith --name Thrain --sub dwarf` |
| A Compendium trait | stack it after a folk: `--sub elf,axis_frost` (traits: `pack compendium`) |
| The Book of Cities' plants, animals, ores, biomes | `packs`, then `pack flora` / `fauna` / `ores` / `biomes` / `races` / `compendium` for a sheet; `gen boc.ore.mithril --seed 1` for one |
| An Aether Library soul (Aelren, Hessel, Tiwa...) | `avatar Aelren --view iso_sw` (a supplement: it never replaces an existing identity) |
| Brackrun-Hollow | `city boc.city.brackrun_hollow <engine>/flavors/boc/packs/aether/brackrun_hollow.names.txt --out bh/` |
| A sandbox world / minigame | `sandbox --biome mountain --seed 3 --out grounds/` (world.json, atlas.png, map.png); to play, the Goblin Grounds page |
| Old-console look | `--era 8-bit` (3 colours), `16-bit`, `32-bit`, `hd` |
| Picture to pixel art | `convert photo.png --tag creature.small --out out.png` |
| Everything it knows | `list` |

Roles are ids like `boc.goblin.shaman`; the full roster of 29 jobs, 2 mounts and 7 clans is in `references/roster.md`. Every command and option is in `references/cli.md`. Packs: `references/use-resource-packs.md`. Goblin Grounds: `references/play-goblin-grounds.md`.

## Rules that keep results right

- **Same name, same goblin.** Never promise a "slightly different" goblin under the same name. For a variation, change the name, the seed, the clan or the variant.
- Treat the pictures as exact. Do not redraw, retouch or "improve" a PixelGoblin picture by hand or with another tool. If something looks wrong, say what and offer a different name, view, size or era.
- Default scale for showing: `--scale 2` or `3` for 64 px and below, so pixels stay visible.
- Side and top views are inferred from the front drawing, not hand-drawn. Small 3D views (16 px) look blocky. Say so if Mark judges them.
- Say which role and options were used, in one line, so the result can be made again.
- Pack colours are mostly **inferred** from names (the source documents rarely state colours). Say so if Mark judges a colour; the fix is a canonical palette in the pack's source catalog, then `tools/build_packs.py`.
- Aether Library avatars are **supplements**: never describe one as replacing a soul's existing appearance.
- Licences: the engine is AGPL-3.0-or-later unless a commercial licence is bought. Each picture carries the licence of the type file that made it: the vanilla pack is CC0-1.0, the goblin (Book of Cities) flavor is Proprietary, owned by Mark. Credit line: "Built on PixelGoblin — © Shibbieness / M MAOU LLC".

## Making new jobs, clans, mounts or cities

Use the `pixelgoblin-types` skill.

## Working on the engine itself

Use the `pixelgoblin-engine` skill (architecture, gates, the JS workbench, how to extend it without breaking the checks).

## References

- `references/roster.md` — every job, mount, clan, variant, view and city
- `references/cli.md` — all 32 commands
- `references/use-resource-packs.md` — folk, traits, packs, CRUCIBLE grounding, avatars
- `references/play-goblin-grounds.md` — the sandbox and minigame
- `references/views.md` — how side, back, isometric and top views are made
- `references/tier-chain.md` — sizes, eras and what each size adds
- `references/build-a-city.md` — the names file and how households work
- `references/use-in-a-game.md`, `references/convert-an-image.md`, `references/make-a-ui-kit.md` — other how-tos
