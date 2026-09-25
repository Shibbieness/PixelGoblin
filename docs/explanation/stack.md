# PixelGoblin in the M MAOU stack

Labels: **Built** means it runs and is checked in this repo. **Designed** means specified here and not yet built.

| Stack piece | What connects | Status |
|---|---|---|
| **Vanilla Core** | PixelGoblin is the second real flavor (`flavor.toml`, `vanilla_flavor.py`, 8 capabilities). It passes the floor and runs through `vanilla-core run`. | **Built** (gate B11) |
| **Vanilla Core, composite runs** | Loading two flavors that share an entry-module name gave the second flavor the first one's code. Fix and regression test: `patches/vanilla-core-composite-fix.patch` (all 40 Vanilla Core tests pass; the new test fails without the fix). | **Built**, as a patch for Mark to apply |
| **QRen Coder** | `examples/composite_qren.py`: PixelGoblin makes a goblin, QRen archives the recipe (type file + seed + pixel hash) as a verified `.xqmem`, then PixelGoblin regenerates identical pixels from the decoded archive. | **Built** (needs the patch above) |
| **SPIRE** | The gate discipline: plan and build gates, falsification with restore-on-start, vacuity guards, count ratchet, from-empty, full-run status, two verdicts, mechanism-first hazards, longevity export. See `gates.md`. | **Built** |
| **SLM-e** | `slme/pieces.json`: 27 deterministic pieces (16 SOLVER, 7 VALIDATOR, SCHEMA, LEXICON, CONSTANT, GATE), each with `degrades_to`. The first 16 passed SLM-e's own `validate_manifest`. The 11 added for characters, scenes and outputs use the same shape, but SLM-e could not be reached from this session to re-run the validator. | **Built**; re-validate the 11 new pieces, then register all 27 in `slme.db` |
| **TINSMITH / GILWRIGHT scrub** | Gate B12 is the scrub: vanilla code and types may not contain stack terms in executable code. Flavor content lives in `flavors/boc/`. | **Built** |
| **Leak guard** | `tools/leakguard.py` from the Sovereign AI Environment repo, run by gate B12, with a planted-trailer control. | **Built** |
| **Book of Cities** | `flavors/boc/`: the goblin rig with the 27 roster roles and 10 subspecies (from Mark's roster reference), the goblin village and HD village scenes (from the village reference), plus the original goblin, aquatic goblin, glowcap fungus and reef backdrop. Python import works directly (`typefile.load`, `gen.frames`). | **Built** (44 types). Catalog-to-type-file script: **Designed** |
| **GILWRIGHT** | First product candidates: (1) the vanilla type-file pack (CC0 sprites), (2) a UI kit pack, (3) the engine under the commercial licence. The scrub is already the manufacturing step. | **Designed** |
| **CRUCIBLE / ASSAY** | `tools/crucible_ramps.py` reads CRUCIBLE's database. A material's electrical resistivity decides the shape of its ramp: metals get a bright glint step. The goblin rig's iron is grey cast iron. CRUCIBLE holds no colour data and ASSAY's CPK colours are a convention, not a material colour, so base colours stay authored. | Ramp shape **Built**; oxide-colour ramps **Designed** |
| **Aether Library** | Deterministic avatars: a name is a seed (`pixelgoblin gen --name`, and the Name field in the workbench), so each AI character always has the same face, at every tier. | **Built** (name seeds); an Aether-side call is **Designed** |
| **Runic / QRen** | Share codes are 19 bytes and could carry a runic rendering. A full recipe fits one QRen archive today. | Share codes **Built**; runic rendering **Designed** |
| **LATTICE / WEAVE** | Docs follow Diátaxis with one subject per page, ready for WEAVE's atomicity and anchor stages. | **Designed** (WEAVE pass not run) |
| **Dropzone** | `pixelgoblin watch ./dropzone`: an `image.png` with an `image.tag` converts automatically into a review queue. | **Built** (polling; no gate yet) |
| **CALS** | A routing rule for the future model slot: "strict palette and commercial → core only; concept exploration → optional model slot, always re-quantised". | **Designed** |

—Shibbieness
—Claude
