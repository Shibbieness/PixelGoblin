# PixelGoblin in VI Builder

VI Builder has no plugin manifest of its own yet (its Phase 1 is not built). A project enters it two ways: as a **Filesystem Source** that the factory ingests, or as an **ML Process** record in the Process Registry. This page gives PixelGoblin both, following the LEXIS registration-profile precedent and the LATTICE/BLOOM Stage 6 `process_record` shape. Everything here is local-first; nothing needs a network.

## Filesystem Source

```
Filesystem source: pixelgoblin/ (local path, DEFAULT; Ingest-on-connect: on)
What L2 will find:  PseudoSKILL.md + SKILL.md + codex/*.INDEX.md (capsule extractor)
                    types/ and flavors/ (*.toml, key-value with schema inference)
                    pixelgoblin/*.py (AST: docstrings and signatures)
                    docs/*.md (structural)
                    *.png (metadata only in Phase 1)
```

The PseudoSkill capsule (`pixelgoblin-pseudoskill.skill`) is the cleanest source: it already has the navigation-map nodes the capsule extractor looks for.

## Registration profile — the knowledge (Tier 4)

```
Process ID:        pixelgoblin-pixel-art-v1
Filesystem source: pixelgoblin-pseudoskill/ (the capsule), or pixelgoblin/ (the repo)
Tier:              4 — Inference
Format type:       4a Prompt Capsule (from PseudoSKILL.md); 4b RAG Package over the type files and packs
Staleness:         MEDIUM — type files, packs and palettes change with the game; the engine contract does not
Routing signal:    pixel art, sprite, goblin, character, tier chain, view, isometric, turnaround, mount, clan,
                   city from names, resource pack, biome, ore weight, sandbox, Goblin Grounds
Castle:            Pixel Art Castle (proposed)
Rooms:             characters (rig, folk, traits) · creatures (fauna, fish) · growing things (flora, fungi) ·
                   materials (ores, CRUCIBLE weights) · places (biomes, villages, cities, Goblin Grounds) · UI (kits, ranks)
Inhabitants:       PixelGoblin (primary); future: art-direction overrides, pose library
Phase relevance:   Phase 1 (Tier 4 Prompt Capsule ingest)
Tags:              #vi-builder-tier4 #cals-namespace
```

## Registration profile — the engine (Tier 2)

```
Process ID:        pixelgoblin-engine-v0u1p0
Tier:              2 — Application
Format type:       2b Start/Stop Job (the command line); 2a System Daemon (the MCP server, stdio)
Staleness:         LOW — gated: 24 build gates, a count ratchet, a from-empty run
Routing signal:    make / draw / render / export pixel art; build a sandbox world
Castle:            Pixel Art Castle (proposed), Room: the forge
Gates (in/out):    type file id + seed or name  →  PNG, GIF, chain.json, world.json
Phase relevance:   Phase 3 (CALS composition engine)
```

## process_record (LATTICE / BLOOM Stage 6 shape)

See `process_record.yaml` beside this page. The three endpoints BLOOM requires map to real commands:

| Endpoint | PixelGoblin |
|---|---|
| query | MCP tool `pixelgoblin_list` (or `python3 -m pixelgoblin list`) |
| status | MCP tool `pixelgoblin_selftest` (or `python3 -m pixelgoblin validate types flavors`) |
| shutdown | close the MCP server's stdin; the command line exits by itself |

## Rules PixelGoblin keeps for VI Builder

- **Local-first.** Python standard library only. The pages load Google Fonts, which is [OPTIONAL]: fallbacks are declared and nothing breaks offline.
- **Mark's vocabulary as given.** Filesystem Source, ML Process, Castle, Rooms, Gates, Inhabitants: used here exactly as VI Builder uses them.
- **No overwrite.** Registering PixelGoblin never writes into another project's files; the Aether Library's no-overwrite rule applies to avatars too.

—Shibbieness
—Claude
