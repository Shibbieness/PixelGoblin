# Gameplan: prototype to standalone

**Rule:** a phase starts only when every gate of the phase before it passes. Every gate is a yes/no test that a program can run. A gate described as "too holistic to check" is a gate nobody checks, so there are none of those here.

## Where things stand (v0u1p0)

The **prototype** is built and gated: Python reference engine, CLI, browser editor with a parity-checked JavaScript core, Vanilla Core flavor, a character rig drawn at six resolution tiers (8 to 256 px) and from any direction, mounts, a village scene composer, a city built from a list of names, Warren dungeons, a pocket widget, a plugin with MCP tools, a PseudoSkill capsule, resource packs from the Book of Cities, the Compendium and the Aether Library, the Goblin Grounds sandbox, and 24 build gates. Plan gates G01 to G32 below are the prototype's exit criteria. `BUILD_STATUS.md` shows which pass.

## Plan gates for the prototype

| Gate | Criterion |
|---|---|
| G01 | One type file and seed give the same pixels in every process and hash seed |
| G02 | Adding a part to a type file changes no existing stream |
| G03 | Whitespace or comment edits leave the type hash unchanged; value edits change it |
| G04 | Every validator refusal is one plain-English sentence naming the field |
| G05 | Decimal numbers are refused anywhere in a type file |
| G06 | Every golden hash reproduces |
| G07 | Every mask sprite passes its spec verdict on 120 seeds |
| G08 | At least 90 of 100 seeds are distinct for each mask type |
| G09 | The blob table has exactly 47 shapes, all visually distinct, and the maps are seamless |
| G10 | WFC always returns an image; the fallback rate is at most 2 in 20 |
| G11 | Conversion never crashes on the fuzz set and never exceeds its colour budget |
| G12 | Pixel-perfect cleanup leaves zero L-corners |
| G13 | 9-slice outlines stay unbroken at five sizes |
| G14 | PNG and ASCII exports round-trip exactly; re-exports are byte-identical |
| G15 | The spec and target verdicts are never merged |
| G16 | A flash above 3 per second is reported, in mechanism order |
| G17 | Non-commercial and share-alike inputs are reported for commercial packs |
| G18 | Every flavor capability runs through the Vanilla Core contract |
| G19 | Vanilla code and types contain no stack terms; no vendor trailers are in the repo |
| G20 | The JavaScript core matches the Python pixels, type hashes and share codes |
| G21 | Every CLI command has help and an example; derived docs are current |
| G22 | The licence text is byte-exact; the credit line shows in `--version` |
| G23 | Share codes round-trip, and a single typo is caught |
| G24 | Brood is deterministic and inherits from both parents |
| G25 | A character is one genome drawn at 8, 16, 32, 64, 128 and 256 px: two legs at every tier, era colour budgets hold, every feature has a rung on the LOD ladder, and silhouette and material coherence stay above the measured floors |
| G26 | Scenes are deterministic and keyed to their characters' type files; every Warren room is reachable; names are seeds; overlays keep the role; animated GIFs keep every frame |
| G27 | Every view is a projection of one lifted model: front and side share heights, front and top widths, side and top depths; the model's front reproduces the drawing; faces are hidden from behind |
| G28 | A city from a list of names is deterministic; adding or removing a citizen changes nobody else; children inherit from their household's parents; a household shares subspecies and clan |
| G29 | No two roles share an 8 px icon; 8-bit eyes survive; items written as data draw; clans change only clothes; riders sit on mounts; zooms grow from crowd to portrait; props gain detail with size |
| G30 | PixelGoblin can be reached from Claude three ways (the Pocket widget, the plugin with its MCP tools, the PseudoSkill capsule); each draws the same pixels as the engine and passes its own structural checks |
| G31 | Resource packs are generated from their source catalogs and stay current; every pack type validates, draws deterministically and matches in JavaScript; folk and traits stack on any job with two legs at every tier; every grounded ore carries CRUCIBLE's own density and every fantasy ore stays ungrounded; avatars are supplements, never overwrites |
| G32 | Goblin Grounds plans the same world in Python and JavaScript; everything gatherable is reachable; quests never ask for more than the world holds; speed falls with the load; the export carries weights for game engines |

## Standalone phases

Each phase lists its gates. Phase numbers match the original design document.

### P0 — Foundations (done in prototype)
- [x] Repo, AGPL and commercial licence files, ADRs, leak guard.
- [x] Gate runner, falsification harness, count ratchet, from-empty run.
- [ ] CI on Linux x86-64, Windows x86-64, macOS ARM (workflow file in `.github/`, first run pending on GitHub).

### P1 — Rust core, bound to the Python goldens
The Python engine becomes the **oracle**. The Rust core must reproduce it.
1. `pixelgoblin-core` crate: rng, typefile (canonical JSON + SHA-256), mask, lsystem, parallax, autotile, wfc, uikit, rig, scene, warren. The rig geometry is already transpiled from Python for JavaScript (`tools/transpile_rig.py`); the same AST walk can emit Rust.
   - **Gate:** every golden in `tests/golden/goldens.json` matches, byte for byte, on all three CI targets plus `wasm32`.
2. Integer-only lint: no `f32`/`f64` in the runtime modules.
   - **Gate:** a CI grep over the runtime modules finds zero float types.
3. Falsification ported: `cargo-mutants` or an equivalent.
   - **Gate:** zero surviving mutants in the runtime modules.

### P2 — Converter quality
1. Edge-aware downsampling, a Wu quantiser, and CIEDE2000 as an optional nearest-colour mode.
2. **Gate:** in a blind A/B on 30 photos and 30 illustrations, PixelGoblin output is chosen over nearest-neighbour at least 80% of the time. Mark judges.
3. **Gate:** a 1024x1024 image converts to 64x64 at 16 colours in under 1.5 s on the dev machine.

### P3 — Runtime and bundles
1. A binary type bundle (`.pwb`, versioned) so games never parse TOML.
2. An LRU cache keyed by `(type_hash, seed, frame)`.
3. **Gate:** a 32x32 mask sprite takes under 0.5 ms median on three machines. **Gate:** the `rt-min` WASM build is under 300 KB.

### P4 — Editor to production
1. Layers and groups, selection and transform, tilemap layers, larger undo history stored as region diffs.
2. Autosave every 60 s and a crash-recovery file.
3. **Gate:** 60 fps on a 512x512 canvas at 8x. **Gate:** a kill test recovers at least 99% of work. **Gate:** 500 random operations followed by 500 undos gives a pixel-identical start.

### P5 — GUI slots, full
1. Dockable panels saved as `layout.toml`. The editor skins itself with a generated UI kit.
2. Bitmap-font packer (BMFont), cursor sets and icon families from `.icon` types.
3. **Gate:** Mark completes five tasks from the tutorials alone: a sprite, a 4-frame walk, a tileset, a UI panel and a conversion.

### P6 — Interop
1. `.ase` read (asefile) and write (from the public spec only), Tiled `.tmj`/`.tsj` with Wang sets, and a Godot `SpriteFrames` `.tres`.
2. **Gate:** 20 files round-trip through Aseprite with layers, tags and palette intact. **Gate:** sheet JSON loads in Phaser, Godot and Unity test projects.

### P7 — Bindings and API
1. PyO3 wheel (replacing the pure-Python engine as the fast path), a WASM npm package, a Godot gdext extension and a C ABI with a C# wrapper.
2. An MCP server with stateless tools that return image content plus a handle; human approval for any file write.
3. **Gate:** the same golden gives the same hash from Python, WASM, Godot and C.

### P8 — Optional model slot (only if wanted)
1. A model registry with a licence field. Non-commercial models are blocked in commercial projects.
2. Every model output is re-quantised to the target palette and size.
3. **Gate:** with the model absent, every earlier gate still passes (the capability floor is run, not asserted).

### P9 — Hardening and release
1. 24 hours of fuzzing with zero crashes; 10,000 generate-and-free cycles with flat memory.
2. Installers, a docs site in the Readable theme, and the published pixel contract.
3. **Gate:** `gate.py --from-empty` passes on a machine that has never seen the repo.

—Shibbieness
—Claude
