# How the build checks itself

PixelGoblin ports the self-checking discipline from SPIRE (Shibbieness / M MAOU LLC). The port is deliberately partial.

## Ported

| SPIRE rule | Here |
|---|---|
| Plan gates (G) and build gates (B) are separate namespaces | `tests/gate.py`; each B declares the Gs it covers |
| A gate must be able to fail | `tests/falsify.py`: 54 mutations, each naming the gate that must catch it |
| Restore on start (SIGKILL cannot be caught) | `falsify.py` **and `gate.py`** restore `.falsify_backup/` before doing anything, so no gate ever tests a leftover mutation. Mutant runs carry `PIXELGOBLIN_MUTANT=1` so their deliberate break is left in place. B10 checks both. |
| No assertion over an empty population | `Check.population()`; every absence check builds a control first |
| Counts are derived, never typed | `tests/FLOOR.json` ratchet; lowering needs a witness and a reason |
| Status only from a full run | `BUILD_STATUS.md` is refused after a partial run |
| Check from empty | `gate.py --from-empty` copies the repo to a clean folder with a minimal environment |
| Tests never touch the network | socket guard in `gate.py` |
| Two verdicts, never merged | spec verdict and target verdict (`verdicts.py`) |
| Mechanism, not prohibition | hazard findings say: don't, what happens, why, what instead |
| Capability floor holds with no model | the whole engine is model-free; ML is a later optional slot |
| Scrub runs against executable code, not prose | B12 skips docstrings and comments; a citation is not a dependency |
| Text is UTF-8 and LF on every OS | B00 parses every `.py` file and fails on text read, written or piped without a named encoding (the platform default is cp1252 on Windows); entry points write UTF-8 to pipes; `.gitattributes` pins LF. CI runs Windows, where the first run failed on exactly these |
| The leak guard opens archives | B12 plants a session link two zips deep and a truncated zip; both must be reported. A built capsule once carried a private link past a guard that only read text |
| Frozen registries | the generator registry is a read-only mapping |
| Longevity export | `pixelgoblin ascii`: a sprite as plain English text |

## Not ported, and why

- **The full hazard register shape.** It exists because chemistry can injure people. PixelGoblin keeps a hazard layer only for the two ways it can hurt someone: **photosensitive flashing** in animations, and **licence contamination** in commercial packs.
- **Held-out splits and grading.** Nothing here is graded.
- **Seven SQLite stores.** Type files are text, which is already the most durable format.

## Build gates

| Gate | Checks | Covers |
|---|---|---|
| B00 | licence text hash, attribution, credit in `--version` | G22 |
| B01 | RNG reference vector, cross-process determinism, part streams | G01 G02 |
| B02 | canonical hash, 20 plain-English validator cases, floats refused | G03 G04 G05 |
| B03 | goldens, spec verdict on 120 seeds per type, variety of 90 or more per 100 | G06 G07 G08 |
| B04 | exactly 47 blob tiles, seamless map, WFC always returns | G09 G10 |
| B05 | conversion fuzz, colour budget, zero L-corners, likeness | G11 G12 |
| B06 | 9-slice unbroken at 5 sizes, four distinct button states | G13 |
| B07 | PNG and ASCII round trips, re-export is byte-identical, share codes | G14 G23 |
| B08 | two verdicts never merged | G15 |
| B09 | flash hazard and licence hazard, in mechanism order | G16 G17 |
| B10 | falsification: every mutant killed | — |
| B11 | Vanilla Core flavor contract | G18 |
| B12 | scrub (vanilla has no stack terms) and leak guard | G19 |
| B13 | JavaScript pixels match Python pixels: sprites, backdrops, tiles, every character at every tier (with subspecies, rim and poses), villages and family trees; the transpiled geometry is current | G20 |
| B14 | every command has help and an example; derived CLI doc is current | G21 |
| B15 | brood inherits from both parents; count ratchet | G24 |
| B16 | characters: every feature is on the LOD ladder, two legs at every tier for every role (with three-leg and merged-leg controls), era colour budgets, coherence floors, the chibi rule, the rim on dark ground | G25 |
| B17 | scenes are deterministic and keyed to their role files, every Warren room is reachable, names are seeds, `_add` appends, overlays keep the role, GIFs keep every frame, cards show six tiers | G26 |
| B18 | views: orthographic agreement (heights, widths, depths), the model's front against the drawing, faces hidden from behind, a full turn returns to the front, the side walk moves in depth | G27 |
| B19 | city: deterministic census, adding or removing a citizen changes nobody else, children inherit from their parents, households share subspecies and clan, the village holds its bands | G28 |
| B20 | 8 px icons are unique, 8-bit eyes use the outline colour, data items draw, clans keep the type hash, riders sit on mounts, zoom sizes, props gain detail with size | G29 |
| B21 | packaging: the pocket widget embeds the current engine; the plugin is valid (manifest, skills, MCP paths); its MCP server writes only protocol messages and draws byte-identical pixels; the PseudoSkill capsule passes every Forge validation check, with a missing-slot control | G30 |
| B22 | resource packs: current with their sources, unique ids, honest manifests, every sprite draws, folk and traits stack with two legs at every tier and keep their stature, grounded ores carry CRUCIBLE's densities and fantasy ores stay ungrounded, avatars are supplements, Brackrun-Hollow builds, JavaScript parity for folk, traits and pack sprites | G31 |
| B23 | Goblin Grounds: everything gatherable is reachable (with a walled-off control), quests fit the world, no two things share a tile, speed falls with load, CRUCIBLE weights reach the export, the page plans the engine's exact world (including a 64-bit seed) | G32 |

—Shibbieness
—Claude
