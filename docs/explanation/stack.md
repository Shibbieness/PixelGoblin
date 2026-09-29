# PixelGoblin in the M MAOU stack

Labels: **Built** means it runs and is checked in this repo. **Designed** means specified here and not yet built.

| Stack piece | What connects | Status |
|---|---|---|
| **Vanilla Core** | PixelGoblin is the second real flavor (`flavor.toml`, `vanilla_flavor.py`, 8 capabilities). It passes the floor and runs through `vanilla-core run`. | **Built** (gate B11) |
| **Vanilla Core, composite runs** | Loading two flavors that share an entry-module name gave the second flavor the first one's code. Fix and regression test: `patches/vanilla-core-composite-fix.patch` (all 40 Vanilla Core tests pass; the new test fails without the fix). | **Built**, as a patch for Mark to apply |
| **QRen Coder** | `examples/composite_qren.py`: PixelGoblin makes a goblin, QRen archives the recipe (type file + seed + pixel hash) as a verified `.xqmem`, then PixelGoblin regenerates identical pixels from the decoded archive. | **Built** (needs the patch above) |
| **SPIRE** | The gate discipline: plan and build gates, falsification with restore-on-start, vacuity guards, count ratchet, from-empty, full-run status, two verdicts, mechanism-first hazards, longevity export. See `gates.md`. | **Built** |
| **SLM-e** | `slme/pieces.json`: 32 deterministic pieces (20 SOLVER, 8 VALIDATOR, SCHEMA, LEXICON, CONSTANT, GATE), each with `degrades_to`. The first 16 passed SLM-e's own `validate_manifest`. The 16 added since (characters, views, mounts, cities, outputs) use the same shape, but SLM-e could not be reached from this session to re-run the validator. | **Built**; re-validate the 16 new pieces, then register all 32 in `slme.db` |
| **TINSMITH / GILWRIGHT scrub** | Gate B12 is the scrub: vanilla code and types may not contain stack terms in executable code. Flavor content lives in `flavors/boc/`. | **Built** |
| **Leak guard** | `tools/leakguard.py` from the Sovereign AI Environment repo, run by gate B12, with a planted-trailer control. Extended here to open archives (`.skill`, `.plugin`, `.zip`, tar), nested ones included, and to report any archive it cannot open. | **Built** |
| **Book of Cities** | `flavors/boc/`: the goblin rig with the 27 roster roles plus a miner and a fisher, 10 subspecies, 7 clans, two mounts (boar and warg) and Goblintown (a city built from a list of names), the goblin village and HD village scenes (from the village reference), plus the original goblin, aquatic goblin, glowcap fungus and reef backdrop. Python import works directly (`typefile.load`, `gen.frames`). | **Built** (48 types: rig roles, subspecies, mounts, scenes, plus a clan file and a city with its population). Catalog-to-type-file script: **Designed** |
| **GILWRIGHT** | First product candidates: (1) the vanilla type-file pack (CC0 sprites), (2) a UI kit pack, (3) the engine under the commercial licence. The scrub is already the manufacturing step. | **Designed** |
| **CRUCIBLE / ASSAY** | `tools/crucible_ramps.py` reads CRUCIBLE's database. A material's electrical resistivity decides the shape of its ramp: metals get a bright glint step. The goblin rig's iron is grey cast iron. CRUCIBLE holds no colour data and ASSAY's CPK colours are a convention, not a material colour, so base colours stay authored. | Ramp shape **Built**; oxide-colour ramps **Designed** |
| **Aether Library** | Deterministic avatars: a name is a seed (`pixelgoblin gen --name`, and the Name field in the workbench), so each AI character always has the same face, at every tier and from every side. A list of names becomes a city with households (`pixelgoblin city`). | **Built** (name seeds, cities); an Aether-side call is **Designed** |
| **Runic / QRen** | Share codes are 19 bytes and could carry a runic rendering. A full recipe fits one QRen archive today. | Share codes **Built**; runic rendering **Designed** |
| **LATTICE / WEAVE** | Docs follow Diátaxis with one subject per page, ready for WEAVE's atomicity and anchor stages. | **Designed** (WEAVE pass not run) |
| **Dropzone** | `pixelgoblin watch ./dropzone`: an `image.png` with an `image.tag` converts automatically into a review queue. | **Built** (polling; no gate yet) |
| **Book of Cities resource packs** | `flavors/boc/packs/`: 37 folk, 9 biomes (sky and ground), 100 plants and fungi, 65 animals and fish, 60 ores, the stations and districts as data (`pixelgoblin packs`). | **Built** (colours mostly inferred; see `docs/howto/use-resource-packs.md`) |
| **Book of Cities Compendium** | Rank badges as UI kits, 14 trait overlays (stackable after a folk), and the Compendium catalog as data. | **Built** (visuals inferred: the Compendium describes mechanics) |
| **Aether Library (souls)** | `packs/aether/souls.toml`: named souls as avatar seeds (`pixelgoblin avatar`), Brackrun-Hollow as a mixed-folk city; supplement-but-never-overwrite. | **Built** (an Aether-side call is **Designed**) |
| **CRUCIBLE (weights)** | Every ore carries CRUCIBLE's density (or says why not); Goblin Grounds weighs gathered ore with it. | **Built** |
| **VI Builder** | `packaging/vi-builder/`: a registration profile (Tier 4a knowledge, Tier 2b engine) and a `process_record` with query, status and shutdown endpoints. | **Designed** (VI Builder's own registry is not built yet) |
| **Goblin Grounds** | The sandbox and minigame: `editor/pixelgoblin-grounds.html` and `pixelgoblin sandbox`. | **Built** (gate B23) |
| **PseudoSkills Builder** | `tools/packaging_capsule.py` forges `pixelgoblin-pseudoskill.skill` in the Builder's capsule structure and runs its validation checklist as code (gate B21). The plugin (`dist/pixelgoblin.plugin`) carries three skills and an MCP server. | **Built** |
| **CALS** | A routing rule for the future model slot: "strict palette and commercial → core only; concept exploration → optional model slot, always re-quantised". | **Designed** |

—Shibbieness
—Claude
