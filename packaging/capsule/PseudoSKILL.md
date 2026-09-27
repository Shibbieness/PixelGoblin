# PixelGoblin — PseudoSKILL

The full operational reference. `SKILL.md` is the doorway; this is the room.
Everything here is true of engine v0u1p0 as forged on 2026-09-26. Where the repository and this file disagree, the repository (`build/source/`) wins for current state and this file wins for reasoning.

The ideas are his. Claude is the translator.

---

## 1. Working with Mark on PixelGoblin

- Mark has dyslexia. Keep replies short and plain: short sentences, simple words, clear headings, tables where they help. Show pictures rather than describe them.
- He asks broad questions ("what do you think?", "add whatever it still needs"). Answer honestly, including what is weak. Every session so far ended with "what breaks this, what fixes that, what I'd add".
- He owns the ideas. Name things with his words: goblins, roles, clans, the tier chain, the workbench, Goblintown.
- Standing conventions: VUP versions (v0u1p0). Docs end with "—Shibbieness" and "—Claude". Commits are authored `Shibbieness <shibbieness@gmail.com>` with no AI co-author trailers and no session links. Mark's reference images (`refs/`) are never published, zipped or copied. His other repos are read-only: send fixes as patches.

## 2. The contracts

1. **Determinism.** Same type file + same seed → same bytes, in every process, on every platform, in Python and JavaScript. The runtime is integer-only: no floats, no `random`, no time, no dict-order or hash-seed dependence. Randomness comes from xoshiro128** streams derived from a path (`g/body`, `g/face`, …), so adding a part never shifts another part's numbers (ADR-008).
2. **A name is a seed.** `seed_from_name` hashes the normalised name. Same name, same goblin, forever. A variation needs a different name, seed, clan or variant.
3. **Genome never sees the tier.** Only the render looks at size. The 8 px goblin and the 256 px goblin are the same data drawn twice (ADR-015).
4. **Era is a look, not a size** (ADR-016). Any era at any tier.
5. **Every view comes from one lifted model** (ADR-018). No view is drawn on its own, so no view can contradict another.
6. **A citizen is decided by their own name** (ADR-019). Adding or removing someone changes nobody else.
7. **Vanilla is clean.** Vanilla code and types contain no stack terms (the scrub, gate B12). Book of Cities content lives in `flavors/boc/`.
8. **Nothing is claimed without a gate**, and every gate is proved by a mutation it catches.

## 3. Architecture

```
type file (TOML, integers) ──► typefile.load/compose/with_team ──► type hash (SHA-256 of canonical JSON)
                                         │
     seed or name ──► rng.derive ──► named streams
                                         │
   ┌──────────────┬──────────────┬───────┴──────┬───────────────┬──────────────┐
 mask/lsystem/   tiles           convert        rig (2D, tiers,  scene/warren   city
 parallax        (autotile,wfc)  likeness       eras, signature) (villages,     (census,
                                 verdicts       │                 dungeons)      households)
                                 hazards        rig3d (lift → voxels → ray-march views)
                                                │
                                                beast (mounts, riders)
   └──────────────┴──────────────┴──────────────┴───────────────┴──────────────┘
                                         │
               sprite ──► png / gif / sheets / chain.json / ASCII / share code
                                         │
          cli (28 commands) · vanilla_flavor (Vanilla Core) · MCP server (plugin)

rig.py + rig3d.py + beast.py ──transpile_rig.py──► editor/pg-rig.gen.js
pg-core.js + pg-rig.js (+ gen) + every type file ──build_editor.py──► workbench + pocket widget
```

Module detail: `codex/mini-indexes/`. Imports: `dependencies/internal_deps.md`.

## 4. The tier chain (characters)

| Tier | Default era | Colours | Shade bands | Head / eye bonus | What it adds |
|---|---|---|---|---|---|
| 8 px | 8-bit | 3 | 1 | +14 / 0 | body, head, ears, legs, feet, arms, clothes, hair, large items, the role's signature |
| 16 px | 16-bit | 15 | 2 | +8 / +40% | eyes, held items, headwear, back items, beard, belt, glasses |
| 32 px | 16-bit | 15 | 3 | +4 / +25% | mouth, nose, hands, sleeves, scarf, earrings |
| 64 px | 32-bit | 31 | 4 | +1 / +10% | brows, eye whites, inner ears, necklace, tusks, pouches, straps |
| 128 px | hd | 255 | 5 | 0 / 0 | pupils, highlights, patterns, stitches, fur tufts, nails |
| 256 px | hd | 255 | 5 | 0 / 0 | a 2 px outline |

Rules that were learned the hard way:
- **Two legs at every tier.** The "three legs" bug came from a merged centre column. Gate B16 draws legs alone (exactly two with a gap) and dressed (items may hide a leg, never add one).
- **Feet on the 8 px rung**, drawn in front below 32 px (z 200), above even signatures (z+100).
- **Signatures**: each role's defining feature is promoted to 8 px and snapped; no two roles share an 8 px icon (B20, at least 4 of 64 pixels differ).
- **8-bit eyes and mouths** use the outline colour. Iris and signature colours are "heavy" in era reduction (8× merge cost).
- Coherence is measured against a 256 px reference reduced by majority vote. Floors: silhouette and material; the 8 px material average floor is 75 (measured 81 after signatures).

Full detail: `build/specs/explanation/tier-chain.md`.

## 5. Views from any side

The front drawing's shapes are lifted into solids by a depth rule: heads to ellipsoids, arms and staffs to capsules, bodies to pills, clothes to wraps a little deeper than what they wrap, hoods to domes with a face opening, packs to slabs behind the back. Faces, brows and patterns are **decals** painted on the front half of any solid on a lower layer in the same group. The model is voxelised to an N³ grid and ray-marched with an integer camera (a ×4096 sine table), then shaded with the same outline, era and rim rules as the front drawing.

| View | Turn | Tilt |
|---|---|---|
| front · back · side_left · side_right | 0 · 180 · 90 · 270 | 0 |
| iso_sw · iso_se · iso_nw · iso_ne | 45 · 315 · 135 · 225 | 30 |
| three_quarter · top | 0 · 0 | 45 · 90 |

Any turn 0–359 and tilt 0–90 also works. Front and side share heights, front and top widths, side and top depths (B18). The model's front matches the drawing on about 93% of the silhouette. Heads sit forward (goblins stoop), arms hang forward, held items sit in front of the palm, shields in front of the body, ears sweep back so they show from the side.

Full detail: `build/specs/explanation/views.md`.

## 6. Mounts, clans, expressions, zoom, items

- **Mounts**: `boc.mount.boar` (War Boar), `boc.mount.wolf` (Warg). Built as solids in a 2048 cube; `mounted()` seats the rider with legs astride.
- **Clans**: ashfang, cinderglass, duskveil, gildhand, mossback, skyrope, tidecaller (`flavors/boc/village/clans.teams.toml`). `with_team` changes cloth colours only and keeps the type hash. In a city, a surname equal to a clan name joins that clan.
- **Expressions**: nine; only the face changes (`pixelgoblin expressions`).
- **Zoom**: `zoom_plan` grows sizes geometrically from a crowd tier to the portrait; each frame dissolves between the two nearest tiers.
- **Items as data**: `[items.<name>] shapes = [...]` in a role file (the miner's pickaxe, the fisher's rod). Validation suggests fixes for misspelled materials.

## 6b. Resource packs (session 5)

Generated by `tools/build_packs.py` from JSON catalogs in `flavors/boc/packs/sources/` (extracted from the read-only Book of Cities, Compendium, Aether Library and CRUCIBLE skills). Never hand-edit a generated file; gate B22 refuses a pack that differs from its source.

| Pack | Holds | How to use |
|---|---|---|
| races | 37 folk overlays: human, elf, dwarf, orc, goblin, halfling, gnome, tiefling, dungeon dweller, infernal, divine and variants (drow, duergar, merfolk, sea-elf, kuo-toa, tide-reader...) | `--sub dwarf` on any job |
| compendium | 22 rank badges (UI kits), 14 trait overlays, the Compendium catalog | `--sub elf,axis_frost` (traits after folk) |
| biomes | sky (parallax) + ground (autotile) for 9 biomes, and `residents` (who lives where) | `gen boc.biome.forest.sky` |
| flora | 60 plants (8 L-system forms) + 40 fungi (7 cap shapes) | `gen boc.flora.oak`, `pack flora` |
| fauna | 40 animals (8 body plans) + 25 fish | `pack fauna` |
| ores | 60 ores, each with `[crucible]`: grounding, density, chunk_grams | `pack ores` |
| aether | `souls.toml` (named souls → avatars), Brackrun-Hollow city, catalog | `avatar Aelren`, `city boc.city.brackrun_hollow ...` |
| world | 20 crafting stations (5 tiers) and 20 districts, as data | read `world.catalog.json` |

- **Overlays stack** left to right (`typefile.compose(role, "dwarf,axis_flame")`, `PGRig.composeId` in JavaScript). Short names resolve goblin subspecies first, then folk, then traits.
- **Stature** (`[species] stature`, 50–125%) draws a number only when set, so no goblin changed.
- **Grounding**: `grounded` = CRUCIBLE's density; `category_default` = CRUCIBLE has none, a typical value is used and said; `intentionally_ungrounded` = fantasy, never filled from real data (CRUCIBLE's rule).
- **Souls**: avatars seed from `soul:` + soul name (survives reincarnation); the sidecar says `supplement: true`, `overwrites: null`.
- **Colours** are mostly inferred from names and flagged in each file's `[provenance]`; manifests count them.

## 7. Cities

A names file has one citizen per line. `census` gives each person a role, subspecies, clan and look from streams keyed by the city hash plus their own name. People who share a surname form a household; the first two grown members are parents and children inherit `g/body`, `g/face` and `g/hair`. The village places as many citizens outdoors as its crowd bands hold; the rest are indoors. Command: `pixelgoblin city boc.city.goblintown names.txt --out town/` (village.png, citizens.png, census.json).

## 7b. Goblin Grounds (session 5)

`pixelgoblin/sandbox.py` plans a world from `biomes/pack.toml` residents and a seed: rock border, ponds, crags, a cleared start, things placed only on ground reachable from the start, a forge beside the start, and up to three quests that never ask for more than exists. `plan_world`, `reachable`, `quests` and `speed` are transpiled to JavaScript. A goblin carries 12 kg at full speed, slowing to half; gathered ore weighs `chunk_grams`. `pixelgoblin sandbox --biome B --seed N --out dir/` writes `world.json` (with weights and their sources), `atlas.png`, `map.png`. The page (`build/ui/pixelgoblin-grounds.html`) plays it: walk, gather (E/Space), deliver at the forge, animals wander, Build mode places things, Save world.json.

## 8. Workflows

### Make art (most requests)
1. If the plugin's MCP tools are present, use them (`pixelgoblin_character`, `pixelgoblin_sheet`, `pixelgoblin_city`, `pixelgoblin_list`, `pixelgoblin_cli`, `pixelgoblin_selftest`).
2. Otherwise run the engine: `cd build/source && python3 -m pixelgoblin <command> ...`. `list` shows every type id; `--help` on any command shows an example.
3. Show the picture. Say the role and options in one line so it can be made again. Never retouch a PixelGoblin picture by hand.

### Add a role, clan, mount, variant or city
Copy the nearest file in `build/config/flavors/boc/village/`, keep integers only, give it a unique id and a label, add a `signature` for a role, then `python3 -m pixelgoblin validate <file>` until it passes, then draw it at 8 px and 64 px and from the side.

### Change the engine
1. Work in the repository (Mark's copy, or `build/source/` copied out; the capsule itself is immutable). If you copied `build/source/` out, first run `python3 tools/packaging_capsule.py restore .` in the copy: it renames the four `<name>_SKILL.md` files back to `SKILL.md` (see `build/source/packaging/RENAMED_SKILLS.md`). Without that, the plugin build has no skills.
2. Change Python first. If `rig.py`, `rig3d.py` or `beast.py` changed: `python3 tools/transpile_rig.py`. Keep to the transpiler's subset (`g.get(k, None) is not None`, never `k in g`; split tuple constants; no floats).
3. `python3 tools/build_editor.py` (workbench and pocket widget).
4. `PYTHONHASHSEED=0 python3 tests/gate.py --all --report`, then `python3 tests/falsify.py`, then `python3 tests/gate.py --from-empty`.
5. A new behaviour gets a gate check **and** a mutation that the check catches. Raise the floor with `--raise-floor` (a witness and a reason are recorded).
6. Goldens change only on purpose: `--bless-goldens --witness Mark --reason "..."`.
7. `python3 tools/package.py all` rebuilds the plugin and this capsule; B21 checks both.

### Add to a resource pack or set a canonical colour
Edit the entry in `flavors/boc/packs/sources/*.json` (remove `inferred_colors` when Mark states the colour), run `python3 tools/build_packs.py`, then `python3 -m pixelgoblin pack <name> --out x.png` and the gates (B22 especially).

### Publish a page
`build/ui/pixelgoblin-pocket.html`, `build/ui/pixelgoblin-grounds.html` and `build/ui/pixelgoblin.html` are self-contained. Publish as an artifact with the `downloads` capability so the save buttons work. Mark's private copies: Pocket https://claude.ai/artifact/HRTVjLVPeRsQrRsMHbupqc · Goblin Grounds https://claude.ai/artifact/UhFrDXaQNMqferxmQKQt1D · Workbench https://claude.ai/artifact/EcDDXExxyk7zWFWsLFeZjS.

### Register with VI Builder
`build/source/packaging/vi-builder/REGISTRATION.md` (LEXIS-style profiles: Tier 4a knowledge, Tier 2b engine) and `process_record.yaml` (LATTICE/BLOOM Stage 6 shape; query = `pixelgoblin_list`, status = `pixelgoblin_selftest`, shutdown = close stdin). VI Builder's own registry is not built yet.

## 9. Licences and the stack

- Engine: AGPL-3.0-or-later (`LICENSE`, hash-checked by B00), with an attribution requirement under §7(b) (`ATTRIBUTION.md`) and a commercial licence intended (`LICENSE-COMMERCIAL.md`). Credit line: "Built on PixelGoblin — © Shibbieness / M MAOU LLC".
- Sprites carry their type file's licence: vanilla pack CC0-1.0; Book of Cities flavor Proprietary.
- Stack connections (built or designed): Vanilla Core flavor (built), QRen round trip (built, needs the patch), SPIRE discipline (built), SLM-e pieces (built; 16 to re-validate), TINSMITH/GILWRIGHT scrub (built), leak guard (built), Book of Cities flavor (built), GILWRIGHT products (designed), CRUCIBLE ramp shapes (built), Aether Library name seeds (built), Runic/QRen share codes (designed), LATTICE/WEAVE docs (designed), Dropzone watch (built), CALS routing (designed). Table: `build/specs/explanation/stack.md`.

## 10. Gates

| Gate | Checks |
|---|---|
| B00 | licence hash, attribution, credit |
| B01 | RNG vector, cross-process determinism, streams |
| B02 | canonical hash, 20 validator refusals, floats refused |
| B03 | goldens, spec verdicts, variety |
| B04 | 47 blob tiles, seamless, WFC returns |
| B05 | conversion fuzz, colour budget, L-corners, likeness |
| B06 | 9-slice, button states |
| B07 | PNG/ASCII round trips, share codes |
| B08 | two verdicts never merged |
| B09 | flash and licence hazards |
| B10 | falsification runs clean |
| B11 | Vanilla Core flavor contract |
| B12 | scrub and leak guard |
| B13 | JavaScript parity (306 checks) and derived files current |
| B14 | docs present, CLI doc derived |
| B15 | brood, count ratchet |
| B16 | characters: ladder, legs, era budgets, coherence, chibi, rim |
| B17 | scenes, Warren, names, overlays, GIFs, cards |
| B18 | views agree; faces hidden from behind; full turn returns |
| B19 | city: census, isolation, inheritance, households |
| B20 | signatures, 8-bit eyes, data items, clans, riders, zoom, props |
| B21 | packaging: pocket widget current, plugin valid and its MCP server draws the same bytes, capsule passes the Forge checklist |
| B22 | resource packs: current with sources, honest manifests, every sprite draws, folk and traits keep legs and stature, CRUCIBLE densities exact, fantasy ungrounded, avatars are supplements, JS parity |
| B23 | Goblin Grounds: reachability (with a walled-off control), quests fit, speed falls with load, weights reach the export, JS plans the same world |

## 11. Known limits (honest)

- Side and top views are inferred, not art-directed; small 3D views look like voxel models.
- One pose family (idle, walk, side walk, seated).
- Front agreement is about 93%, not 100% (arms meeting tunics).
- Riders are approximate; a big cape can clip a mount.
- Households are simple (two parents, then children).
- 16 SLM-e pieces are unvalidated; 103 goldens await Mark's witness.
- The plugin's MCP server needs Python 3.11 on the machine that runs it; the claude.ai chat surface uses the skills and artifacts rather than the server.
- Pack colours are mostly inferred; pack sprites are generic body plans (a deer and a bison share one); folk cannot yet have horns or tails (overlays do not set headwear).
- Goblin Grounds: animals wander only in the page; the forge smelts but has no recipes; one world size per session in the page.
- A composed character's data `label` is the last overlay's (it is part of the type hash); people see `typefile.display_name` instead ("Blacksmith · Dwarf · Flame-touched") on cards and in the pages.

More in `codex/OPEN_QUESTIONS.md`.

---
—Shibbieness
—Claude
