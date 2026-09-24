# PixelGoblin in the M MAOU stack

Labels: **Built** means it runs and is checked in this repo. **Designed** means specified here and not yet built.

| Stack piece | What connects | Status |
|---|---|---|
| **Vanilla Core** | PixelGoblin is the second real flavor (`flavor.toml`, `vanilla_flavor.py`, 8 capabilities). It passes the floor and runs through `vanilla-core run`. | **Built** (gate B11) |
| **Vanilla Core, composite runs** | Loading two flavors that share an entry-module name gave the second flavor the first one's code. Fix and regression test: `patches/vanilla-core-composite-fix.patch` (all 40 Vanilla Core tests pass; the new test fails without the fix). | **Built**, as a patch for Mark to apply |
| **QRen Coder** | `examples/composite_qren.py`: PixelGoblin makes a goblin, QRen archives the recipe (type file + seed + pixel hash) as a verified `.xqmem`, then PixelGoblin regenerates identical pixels from the decoded archive. | **Built** (needs the patch above) |
| **SPIRE** | The gate discipline: plan and build gates, falsification with restore-on-start, vacuity guards, count ratchet, from-empty, full-run status, two verdicts, mechanism-first hazards, longevity export. See `gates.md`. | **Built** |
| **SLM-e** | `slme/pieces.json`: 16 deterministic pieces (8 SOLVER, 4 VALIDATOR, SCHEMA, LEXICON, CONSTANT, GATE), each with `degrades_to`. All 16 pass SLM-e's own `validate_manifest`. | **Built**; registering them in `slme.db` is the next step |
| **TINSMITH / GILWRIGHT scrub** | Gate B12 is the scrub: vanilla code and types may not contain stack terms in executable code. Flavor content lives in `flavors/boc/`. | **Built** |
| **Leak guard** | `tools/leakguard.py` from the Sovereign AI Environment repo, run by gate B12, with a planted-trailer control. | **Built** |
| **Book of Cities** | `flavors/boc/`: goblin, aquatic goblin (via `extends`), glowcap fungus and reef backdrop. Python import works directly (`typefile.load`, `gen.frames`). | **Built** (4 types). Catalog-to-type-file script: **Designed** |
| **GILWRIGHT** | First product candidates: (1) the vanilla type-file pack (CC0 sprites), (2) a UI kit pack, (3) the engine under the commercial licence. The scrub is already the manufacturing step. | **Designed** |
| **CRUCIBLE / ASSAY** | Material-true ramps: an ore's ramp derived from its real oxide colours (copper to verdigris). This feeds `palette.ramps` in `ore.*` types. | **Designed** |
| **Aether Library** | Deterministic avatars: `seed = hash(agent id)` over a character species type, so each AI character always has the same face. | **Designed** (the engine already supports it) |
| **Runic / QRen** | Share codes are 19 bytes and could carry a runic rendering. A full recipe fits one QRen archive today. | Share codes **Built**; runic rendering **Designed** |
| **LATTICE / WEAVE** | Docs follow Diátaxis with one subject per page, ready for WEAVE's atomicity and anchor stages. | **Designed** (WEAVE pass not run) |
| **Dropzone** | `pixelgoblin watch ./dropzone`: an `image.png` with an `image.tag` converts automatically into a review queue. | **Designed** |
| **CALS** | A routing rule for the future model slot: "strict palette and commercial → core only; concept exploration → optional model slot, always re-quantised". | **Designed** |

—Shibbieness
—Claude
