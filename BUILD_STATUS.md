# BUILD_STATUS

PixelGoblin v0u1p0 · engine major 0

Written only when every build gate ran. Counts below are derived by the run, not typed.

- Build gates passed: 16 of 18
- Plan gates covered by passing build gates: 23 of 26
- Assertions: 1111

| Gate | What | Covers | Result |
|---|---|---|---|
| B00 | skeleton, licence and attribution | G22 | PASS |
| B01 | randomness and seed derivation | G01, G02 | PASS |
| B02 | type files: hashing, validation, integer-only | G03, G04, G05 | PASS |
| B03 | generators: goldens, constraints, variety | G06, G07, G08 | FAIL |
| B04 | tiles: 47-blob table and WFC | G09, G10 | PASS |
| B05 | image + tag conversion | G11, G12 | PASS |
| B06 | UI kit (GUI slots) | G13 | PASS |
| B07 | I/O, export, provenance, share codes | G14, G23 | PASS |
| B08 | two verdicts, never merged | G15 | PASS |
| B09 | hazard layer: flashing and licences | G16, G17 | PASS |
| B10 | falsification (mutation testing) | — | FAIL |
| B11 | Vanilla Core flavor contract | G18 | PASS |
| B12 | scrub (vanilla vs flavor) and leak guard | G19 | PASS |
| B13 | cross-language parity (JavaScript editor core, rig, scene) | G20 | PASS |
| B14 | documentation is present and derived docs are current | G21 | PASS |
| B15 | brood and the count ratchet | G24 | PASS |
| B16 | characters: one genome, six tiers | G25 | PASS |
| B17 | scenes, dungeons, names, overlays and outputs | G26 | PASS |

## Ratchet

| Count | Now | Floor |
|---|---|---|
| build_gates | 18 | 18 |
| plan_gates_covered | 26 | 26 |
| goldens | 208 | 208 |
| validator_negative_cases | 20 | 20 |
| mutations | 34 | 34 |
| vanilla_types | 10 | 10 |
| flavor_types | 44 | 44 |
| cli_commands | 21 | 21 |
| flavor_capabilities | 8 | 8 |
| tag_roots | 8 | 8 |
| doc_pages | 14 | 14 |

—Shibbieness
—Claude
