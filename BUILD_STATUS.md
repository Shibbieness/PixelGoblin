# BUILD_STATUS

PixelGoblin v0u1p0 · engine major 0

Written only when every build gate ran. Counts below are derived by the run, not typed.

- Build gates passed: 16 of 16
- Plan gates covered by passing build gates: 24 of 24
- Assertions: 513

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
| B13 | cross-language parity (JavaScript editor core) | G20 | PASS |
| B14 | documentation is present and derived docs are current | G21 | PASS |
| B15 | brood and the count ratchet | G24 | PASS |

## Ratchet

| Count | Now | Floor |
|---|---|---|
| build_gates | 16 | 16 |
| plan_gates_covered | 24 | 24 |
| goldens | 43 | 43 |
| validator_negative_cases | 20 | 20 |
| mutations | 23 | 23 |
| vanilla_types | 8 | 8 |
| flavor_types | 4 | 4 |
| cli_commands | 14 | 14 |
| flavor_capabilities | 8 | 8 |
| tag_roots | 8 | 8 |
| doc_pages | 13 | 13 |

—Shibbieness
—Claude
