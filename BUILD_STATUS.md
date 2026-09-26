# BUILD_STATUS

PixelGoblin v0u1p0 · engine major 0

Written only when every build gate ran. Counts below are derived by the run, not typed.

- Build gates passed: 24 of 24
- Plan gates covered by passing build gates: 32 of 32
- Assertions: 5463

| Gate | What | Covers | Result |
|---|---|---|---|
| B00 | skeleton, licence and attribution | G22 | PASS |
| B01 | randomness and seed derivation | G01, G02 | PASS |
| B02 | type files: hashing, validation, integer-only | G03, G04, G05 | PASS |
| B03 | generators: goldens, constraints, variety | G06, G07, G08 | PASS |
| B04 | tiles: 47-blob table and WFC | G09, G10 | PASS |
| B05 | image + tag conversion | G11, G12 | PASS |
| B06 | UI kit (GUI slots) | G13 | PASS |
| B07 | I/O, export, provenance, share codes | G14, G23 | PASS |
| B08 | two verdicts, never merged | G15 | PASS |
| B09 | hazard layer: flashing and licences | G16, G17 | PASS |
| B10 | falsification (mutation testing) | — | PASS |
| B11 | Vanilla Core flavor contract | G18 | PASS |
| B12 | scrub (vanilla vs flavor) and leak guard | G19 | PASS |
| B13 | cross-language parity (JavaScript: core, rig, views, beasts, city) | G20 | PASS |
| B14 | documentation is present and derived docs are current | G21 | PASS |
| B15 | brood and the count ratchet | G24 | PASS |
| B16 | characters: one genome, six tiers | G25 | PASS |
| B17 | scenes, dungeons, names, overlays and outputs | G26 | PASS |
| B18 | views: one lifted model, seen from anywhere | G27 | PASS |
| B19 | city: a population from a list of names | G28 | PASS |
| B20 | signatures, items as data, clans, mounts, zoom, props | G29 | PASS |
| B21 | packaging: pocket widget, plugin and PseudoSkill capsule | G30 | PASS |
| B22 | resource packs: Book of Cities, Compendium, Aether Library, CRUCIBLE | G31 | PASS |
| B23 | Goblin Grounds: a sandbox world from the packs | G32 | PASS |

## Ratchet

| Count | Now | Floor |
|---|---|---|
| build_gates | 24 | 24 |
| plan_gates_covered | 32 | 32 |
| goldens | 224 | 224 |
| validator_negative_cases | 20 | 20 |
| mutations | 51 | 51 |
| vanilla_types | 10 | 10 |
| flavor_types | 364 | 364 |
| cli_commands | 32 | 32 |
| flavor_capabilities | 8 | 8 |
| tag_roots | 8 | 8 |
| doc_pages | 19 | 19 |

—Shibbieness
—Claude
