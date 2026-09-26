---
name: pixelgoblin-types
description: This skill should be used when the user asks to "add a new goblin job", "make a new role", "make a new clan", "add a mount", "make a new city", "add a new race / folk", "add a plant / animal / ore to the pack", "fix a pack colour", "write a type file", "make a new species", "give the miner a pickaxe", "change what a role wears or holds", or otherwise wants to create or edit PixelGoblin type files (TOML) or resource packs.
---

# PixelGoblin type files

Everything PixelGoblin draws comes from small TOML **type files**. New jobs, clans, mounts and cities are data, not code. Write the file, validate it, draw it.

The engine lives in the `pixelgoblin` skill's `engine/` folder (a sibling of this skill: `../pixelgoblin/engine`). If that path is missing, find it with `find / -path '*pixelgoblin/engine/pixelgoblin/cli.py' 2>/dev/null | head -1`. If the `pixelgoblin_cli` MCP tool is present, it can run `validate` and draw the result.

## Talking to Mark

Mark has dyslexia. Keep replies short and plain. Show the new goblin as a picture; show the TOML only if he asks or needs to edit it.

## Workflow

1. **Start from the nearest existing file.** Copy it, do not write from nothing. Examples in the engine:
   - job: `flavors/boc/village/roles/miner.toml` (it holds an item written as data, a pickaxe)
   - variant: `flavors/boc/village/subspecies/*.toml`
   - mount: `flavors/boc/village/mounts/boar.beast.toml`
   - clans: `flavors/boc/village/clans.teams.toml`
   - city: `flavors/boc/village/goblintown.city.toml` with `goblintown.names.txt`
   Use `find flavors -name '*.toml'` in the engine folder to see them all.
2. **Keep the rules**: whole numbers only (decimals are refused, so every platform makes the same pixels); a unique dotted `id`; `schema = "pixelgoblin/type@1"`; a `license` for the sprites; a `label`.
3. **Put new files in the user's own folder**, not inside the engine, unless the user asks. For the engine to find them by id, place them under `engine/flavors/<name>/`; otherwise pass the file path instead of the id.
4. **Validate**: `python3 -m pixelgoblin validate path/to/file.toml`. It explains every problem in plain English. Fix and repeat until it passes.
5. **Draw it** at a few sizes: `card path/to/file.toml --name Test`, and one side view. Check at 8 px that the job's signature item still reads (every job must look different from every other at 8 px).
6. Show the picture. Say the new id and how to use it.

## Things that catch people out

- A role `extends` the species; tables merge, lists replace; a key ending in `_add` appends to the parent's list.
- A variant overlay only applies its own keys: a snow blacksmith keeps the blacksmith's clothes.
- A clan changes clothes colours only. Face, build and job stay. The type hash stays the role's own.
- An item written as data (`held_spec`, `offhand_spec`) needs a shape list; copy the miner's pickaxe block and change it.
- A new job needs a `signature` (the one thing that identifies it at 8 px), or it may be drawn the same as another job.
- In a names file, one citizen per line; a surname that matches a clan name joins that clan; people with the same surname form a household.

## Resource packs are generated: change the source, not the pack

Everything in `flavors/boc/packs/` except `sources/` is written by `tools/build_packs.py` from the JSON catalogs in `flavors/boc/packs/sources/` (extracted from the Book of Cities, the Compendium, the Aether Library and CRUCIBLE). To add a folk, plant, animal or ore, or to set a canonical colour:

1. Edit the matching entry in `sources/boc.json` (or `compendium.json`, `aether.json`). Colours may be words ("rust red") or hex. Remove `"inferred_colors": true` when Mark has stated the colour.
2. Run `python3 tools/build_packs.py` from the engine folder (the repository root in a full checkout).
3. Validate and draw: `python3 -m pixelgoblin pack ores --out ores.png`.
4. Never edit a generated pack file by hand: gate B22 refuses a pack that differs from its source.

Rules the packs keep: fantasy ores stay `intentionally_ungrounded` (CRUCIBLE's rule); folk and traits are overlays (their `[role]` is ignored); Aether avatars are supplements, never overwrites.

## Reference

- `references/type-files.md` — every field for every generator (rig, beast, scene, mask, lsystem, autotile, uikit, parallax, warren), clans and cities
- `references/make-a-species.md` — tutorial: a new species from scratch
- the `pixelgoblin` skill's `references/use-resource-packs.md` — the packs, overlays and CRUCIBLE grounding
