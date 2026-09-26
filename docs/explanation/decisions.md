# Decisions (ADRs)

Format: **Context → Decision → Consequences.** ADR-001 to ADR-008 are from the design document of 2026-09-24. ADR-009 onward were made during the prototype build.

| ADR | Decision | Status |
|---|---|---|
| 001 | One core, many thin bindings | Kept; the core is Python for now (see 009) |
| 002 | Integer-only runtime; floats only at tool time | **Built and gated** (B02 refuses floats, B13 proves cross-language) |
| 003 | Model-free core; ML is an optional plug-in | Built: there is no ML anywhere |
| 004 | Own quantiser; no libimagequant | Built: seeded-free k-means in OKLab |
| 005 | TOML authored, canonical JSON hashed | Built with SHA-256 (BLAKE3 is not in the stdlib) |
| 006 | Editor UI in Rust + egui | **Superseded by 011** for the prototype |
| 007 | Aseprite interop from the public spec only | Planned (P6); Aseprite-style sheet JSON ships now |
| 008 | Named sub-seed streams per part | **Built and gated** (B01, and a falsify mutation) |

ADR-009 to ADR-023 follow below, one section each.

## ADR-009 — Python reference engine before Rust (reverses the build order)

**Context.** The design said: build the Rust core first. That was the right call for speed, but three things pointed the other way for the prototype. Book of Cities is sovereign Python and the first real consumer. The stack's discipline (SPIRE, Vanilla Core, ASSAY) is stdlib-only Python with zero dependencies. And a determinism contract needs an **oracle** to port against.

**Decision.** The prototype engine is stdlib-only Python. It is the reference implementation and the owner of the goldens. The Rust core (P1) must reproduce its goldens byte for byte.

**Consequences.** + Runs today with nothing installed. + Imports directly into Book of Cities. + The goldens become the spec for every later port. − Slower than Rust; fine for tools and load-time generation, and not for per-frame generation of large crowds.

## ADR-010 — Licensing: follow the stack's existing pattern

**Context.** Mark wants it open source "unless they want to pay for it". QRen Coder and Vanilla Core already solve this exact problem: AGPL-3.0-or-later, plus a placeholder commercial licence, plus a small §7(b) attribution term, with the bigger credit obligation kept in the private commercial contract.

**Decision.** PixelGoblin uses the same three files, with the same wording and structure. Two additions specific to pixel art:
1. **Output is not covered by the engine's licence.** Each type file's `license` field states the licence of the *sprites* it makes, and that licence is written into every export's provenance.
2. **Vanilla type files make CC0 sprites.** This gets the art out there with no strings. Book of Cities flavor types are `Proprietary`.

**Consequences.** + Indies and jams pay nothing and owe only a credit line. + Closed-source games that embed the runtime are the natural buyers of the commercial licence. − The commercial terms still need a lawyer (placeholder).

## ADR-011 — Editor as one offline HTML page, with a parity-gated JavaScript core

**Context.** An egui editor needs the Rust core, which does not exist yet. A page that runs in any browser can be opened today, shared as a link, and embedded.

**Decision.** `editor/pixelgoblin.html` is built from `editor/src.html` and `editor/pg-core.js`, a line-for-line port of the integer runtime. Gate B13 runs `pg-core.js` under node and requires identical pixels, type hashes and share codes for every golden.

**Consequences.** + A usable editor now, on any device. + A second-language proof of the determinism contract. − Two implementations to keep in step. The gate makes drift loud rather than silent.

## ADR-012 — What was ported from SPIRE, and what was not

**Decision.** Port the gate discipline: namespaces, falsification, vacuity guards, ratchets, from-empty, full-run status, socket guard, two verdicts, mechanism-first hazards, scrub on code not prose, and the longevity export. Do **not** port the hazard register's full shape, held-out splits, or the seven-store layout. See `gates.md` for the reasons.

## ADR-013 — Two verdicts: spec and target

**Context.** "Is this goblin right?" and "can the NES show this goblin?" are different questions. Merged, a platform limit reads as a design error.

**Decision.** `spec_verdict` (SOUND / UNSOUND) and `target_verdict` (FITS / DOES_NOT_FIT) are separate functions with no combined field. Gate B08 and a falsify mutation hold this.

## ADR-014 — The hazard layer: flashing and licences only

**Context.** Pixel art tools make animations. Fast light/dark flashing can trigger seizures.

**Decision.** Animation exports run an approximate WCAG-style general-flash check. Findings are labelled UNVERIFIED, because this is not a certified test, and are delivered in SPIRE's order: don't, what happens, why, what instead. Detection reports and never blocks on its own. Blocking is a bundle-profile judgement, used only for commercial packs with non-commercial inputs.

## ADR-015 — Characters: a genome that never sees the tier

**Context.** Mark wants a character to "translate up and down in pixel resolution" from 8 to 256 px. Hand-made sprite chains redraw a character at every size, and the redraws drift.

**Decision.** A rig character is split into a **genome** (what it is, decoded once from named streams) and a **render** (how it is drawn at one tier). Only the render reads the tier: the LOD ladder, shade bands, outline, and the chibi head and eye bonus. All geometry lives in a 1024-unit design space that every tier divides evenly.

**Consequences.** + Identity across tiers is measurable (coherence) and checkable (legs, era budgets) per role. + A name, a seed or a family tree fixes a character at every size at once. − 8 px is an icon, not a copy; that is measured and stated, not hidden.

## ADR-016 — "Bit" is an era look, not a size

**Context.** The request named 8- to 256-"bit" characters. Console "bits" are CPU generations, and 128- and 256-bit consoles have no distinct pixel-art style.

**Decision.** Keep two settings, never merged: the **tier** (8 to 256 px) and the **era** (8-bit, 16-bit, 32-bit, HD: colour budget, bands, outline, dither). A build bit chain uses a default era per tier; any era can be forced at any tier.

**Consequences.** + Both readings of the request work. + An 8-bit-look HD sprite is expressible. − One more word to learn; `tier-chain.md` explains it.

## ADR-017 — The JavaScript character geometry is generated, not ported

**Context.** ADR-011 ports the runtime to JavaScript line for line. The rig's geometry is about 400 lines of dense integer arithmetic, and hand copies of that would drift.

**Decision.** `tools/transpile_rig.py` walks the Python AST of the geometry functions and emits `editor/pg-rig.gen.js`. It handles only the small integer subset those functions use (floor division and modulo with Python semantics, `in`, `.get`, `.append`) and refuses anything else by name. Gate B13 regenerates it and fails if the committed copy differs, and then compares pixels at every tier. The render loop around it stays hand-ported and parity-gated.

**Consequences.** + Geometry changes cannot silently skip the editor. + The same AST walk can target Rust in P1. − Geometry must stay inside the documented subset.

## ADR-018 — Views are built by lifting the front drawing, not by drawing each view

**Context.** Mark asked for side, isometric, top-down and free-rotating views that "build from each other". Characters are generated, so there are no hand-drawn side views to combine.

**Decision.** `gen/rig3d.py` lifts every front shape into a solid by a depth rule for its feature. Faces and patterns become decals painted from the front. The solids fill a voxel grid, and an orthographic camera at any yaw and pitch draws the view. The finish (bands, contact shadows, outline, era) is the front drawing's own. The code is transpiled to JavaScript, like the geometry.

**Consequences.** + Every view agrees with every other (gate B18), and the model's front reproduces the drawing. + Free rotation in the workbench. − Side and top views are inferred, not art-directed. Per-feature depth overrides as data are the next step.

## ADR-019 — A citizen is decided by their own name

**Context.** A city of hundreds must be reproducible from a list of names, and editing the list must not reshuffle everyone.

**Decision.** Each citizen's randomness comes from streams seeded by their own name and the city file's hash. A household is a surname. Children inherit whole streams (body, face, hair) from their household's first two grown members.

**Consequences.** + Adding or removing a citizen changes nobody else (gate B19). − A household's children depend on who its parents are, by design.

## ADR-020 — Mounts are built as solids from the start

**Context.** A quadruped is long from front to back; a front drawing says almost nothing about it.

**Decision.** `gen/beast.py` builds beasts directly as 3D solids in a cube twice the goblin's, and seats a rider by moving its lifted model onto the saddle with the legs re-posed. Decals carry a group, so a rider's face never paints onto its mount.

**Consequences.** + Every view of a mount and rider comes from the same renderer as the goblins. − Beasts have no front *drawing* to check against; their gates are about the rig, not a drawing.

## ADR-021 — Three ways in from Claude, one engine behind them

**Context.** Mark asked for a widget, a plugin "for all of it", access in future chats, and the whole project packaged as a PseudoSkill. Different surfaces run different things: a published page runs JavaScript only; a plugin can run a local Python server; a skill capsule is read by Claude and may or may not have a shell.

**Decision.** Three surfaces, each doing one job, none with its own copy of the logic. The **Pocket widget** is built by `tools/build_editor.py` from the same engine script as the workbench. The **plugin** bundles the engine inside its main skill (so the skill works even where only the skill folder is uploaded) and adds an MCP server that runs `cli.main` in the same process with stdout captured, so it returns the command line's exact bytes. The **PseudoSkill capsule** is forged by `tools/packaging_capsule.py` from one item table; indexes, tags, the dependency graph, the changelog and pretune hashes are generated, and the Forge validation checklist runs as code before anything is zipped. Gate B21 builds the plugin and capsule in a temporary folder and checks all three.

**Consequences.** + Same name, same goblin everywhere, proved by a gate. + The capsule cannot drift from the repository, because it is regenerated from it. − The MCP server needs Python 3.11 where it runs. − The capsule is a snapshot; changes after the forge go through Companion Builder mode or a re-forge.

## ADR-022 — Resource packs are generated from source catalogs, never hand-edited

**Context.** Mark asked for basic resource packs "of and for all of the stuff" in the Book of Cities, the Compendium and the Aether Library. Those projects are large, still growing, and read-only to PixelGoblin; their documents describe mechanics far more than looks.

**Decision.** Each source is extracted once into a JSON catalog (`flavors/boc/packs/sources/`), and `tools/build_packs.py` turns the catalogs into ordinary type files, one folder and `pack.toml` per pack. Folk and traits are **overlays**, so any job can be any folk, and overlays stack left to right. Colours named in words are resolved at tool time; every inferred colour is flagged. Ores carry CRUCIBLE's densities, and fantasy materials stay `intentionally_ungrounded`, as CRUCIBLE requires. Aether avatars are seeded from the soul name and marked as supplements.

**Consequences.** + Every Book of Cities creature, plant and ore can be drawn today, from the command line, the workbench, the Pocket, the plugin and Goblin Grounds. + When a source changes, one command regenerates the pack and gate B22 refuses a stale one. − Most colours are guesses until Mark sets canonical palettes. − The mask icons are generic body plans, not hand-drawn creatures.

## ADR-023 — Goblin Grounds: the engine owns the world, the page owns the play

**Context.** Mark asked for a sandbox and minigame area, using CRUCIBLE and VI Builder. A minigame in a browser and a world file for a game engine must not disagree.

**Decision.** `pixelgoblin/sandbox.py` plans the world (tiles, things, start, forge, quests) in the transpiler's integer subset, and the page runs the transpiled planner. Gathering weight is CRUCIBLE's density times a 500 cm³ chunk; carrying slows the goblin. VI Builder has no manifest yet, so PixelGoblin registers the LEXIS way (a registration profile) and the LATTICE way (a `process_record` with query, status and shutdown endpoints), in `packaging/vi-builder/`.

**Consequences.** + The same biome and seed make the same world in the page and in `world.json` (gate B23 checks both). + The minigame is a real test of the packs: if an ore's weight is wrong, you feel it. − Animals do not move yet; the forge smelts but crafting has no recipes. Both are the next layer.

—Shibbieness
—Claude
