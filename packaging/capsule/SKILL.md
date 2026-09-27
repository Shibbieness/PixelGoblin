---
name: pixelgoblin-pseudoskill
description: "PixelGoblin is Shibbieness's deterministic pixel-art engine: one name makes the same character at every size from 8 to 256 px, from any side, as any folk of the Book of Cities, in clan colours, on a mount, in a town built from a list of names, or walking a Goblin Grounds sandbox world whose ores weigh what CRUCIBLE says, all with the Python standard library and pixel-identical browser pages. Load this skill when PixelGoblin, its goblins or folk, the tier chain, views, mounts, clans, cities, the resource packs, Goblin Grounds, the workbench, the Pocket, the plugin, its gates, or its place in the M MAOU stack comes up. With it loaded, Claude can make art with the bundled engine, extend the engine and packs without breaking their gates, answer why any decision was made, and route to the right file without a briefing."
metadata:
  version: "v1u0p1"
  version_format: "VUP"
  author: "Shibbieness (Mark)"
  co_author: "Claude"
  organization: "M MAOU LLC"
  forged: "2026-09-26"
  build_mode: "compound"
  immutable_core: "true"
  update_structure_version: "1.0"
  built_using: "pseudoskills-builder (Compound Build mode, dense-session protocol)"
  composes_with: "spire, slm-e, book-of-cities, book-of-cities-compendium-builder, aether-library-pseudoskill, crucible, vi-builder, gilwright, dropzone, cals, working-with-mark, eexpand"
  companions: "the pixelgoblin plugin (tools), working-with-mark (operational pairing)"
---

> ⚠️ IMMUTABILITY NOTICE
>
> This pseudo-skill capsule is read-only. Its core files, documentation, code,
> dependencies, and index structures cannot be modified by the Project Codex Compiler
> or the Companion Builder mode. These tools create; they do not edit.
>
> To add new artifacts (companions, guides, tests, documentation): use Companion Builder mode.
> New additions index into the updates/ layer only.
>
> To structurally modify this capsule: use the Pseudo-Skill Update Skill (separate tool).
> Attempting modification through any other tool is outside that tool's scope.
> To re-forge: run `python3 tools/package.py capsule` in the repository.
>
> This notice is a feature, not a warning. The constraint is the trustworthiness.

# PixelGoblin PseudoSkill

The ideas are his. Claude is the translator.

**State on load:** this file is the doorway. The full operational reference is `PseudoSKILL.md` (the room). The whole repository is in `build/source/` and runs from there: `cd build/source && python3 -m pixelgoblin --help`.

## Project Identity

| Field | Value |
|---|---|
| Project Name | PixelGoblin |
| Short Name | PG |
| Author | Shibbieness (Mark) |
| Organization | M MAOU LLC |
| Current Status | Active |
| Version | engine v0u1p0 (engine major 0) · capsule v1u0p0 |
| Forged | 2026-09-26 |
| CALS Namespace | Yes |
| Build Present | Yes (complete, runnable, gated) |

## What This Project Is

PixelGoblin makes pixel art three ways from one small engine: it **generates** sprites from a type file plus a seed, **converts** any image into pixel art that fits a tag, and **learns** a type file from one example. It also builds 47-tile autotile sets, seamless textures, parallax backdrops, UI kits, villages and Warren dungeons. The same type file and seed make the same bytes in every process, in Python and in the browser.

Its heart is the goblin **rig**. A character is one **genome** that never sees the **tier**; it is drawn at 8, 16, 32, 64, 128 and 256 px, each tier adding features on the **LOD ladder**, each with an **era** look (8-bit, 16-bit, 32-bit, HD). A **name is a seed**, so Grubnak is always Grubnak. The front drawing is **lifted** into one 3D model, so every view (side, back, isometric, top-down, any turn and tilt) is a projection of the same goblin and the views agree like a draughtsman's. Goblins wear **clan** colours, ride **mounts** (war boar, warg), show nine **expressions**, **zoom** from crowd size to portrait, and a list of names becomes a **city** of households whose children resemble their parents.

The **resource packs** bring Mark's other worlds in as data: 37 **folk** of the Book of Cities (overlays for any job, with their own stature), 9 biomes, 165 plants, fungi, animals and fish, 60 ores **grounded** in CRUCIBLE, the Compendium's ranks and **traits** (overlays that stack after a folk), and the Aether Library's **souls**, whose avatars are **supplements**, never overwrites. **Goblin Grounds** puts it all to use: a sandbox and minigame where a goblin gathers weighed ore for the forge, planned by the engine so the page and a game's `world.json` agree exactly.

It is built under SPIRE's discipline: 24 build gates (B00 to B23) covering 32 plan gates (G01 to G32), 51 mutations that must all be caught, 224 goldens, a count ratchet and a from-empty run. It is standard-library Python with an integer-only runtime; the JavaScript workbench is partly transpiled from the Python and proved pixel-identical. The engine is AGPL-3.0-or-later with a commercial licence intended; the Book of Cities goblin flavor is Proprietary to Mark.

Mark reaches it three ways: the **Pocket**, **Goblin Grounds** and the **Workbench** (published artifacts), the **pixelgoblin plugin** (three skills plus nine MCP tools that return pictures), and this capsule, which is the project's memory. VI Builder can ingest it through the registration profile in `build/source/packaging/vi-builder/`.

## Navigation Map

### Start Here
- `PseudoSKILL.md` — the full operational reference: contracts, architecture, workflows, rules. Go here for anything this router does not answer.
- `codex/MASTER_INDEX.md` — every indexed item with tags, plus a concept-to-item table. Go here first for any lookup.
- `codex/NARRATIVE.md` — the story of sessions 1 to 5 and why things are the way they are. Go here when history or reasoning matters.
- `codex/CALS_NAMESPACE.md` — how work routes between the engine's parts, the gates and the optional model slot. Go here before deciding where a change belongs.

### For Technical Work
- `build/source/` — the complete repository, runnable. Go here to make art or change code. Its inner skill files are renamed `<name>_SKILL.md` so this capsule has one `SKILL.md`; `build/source/packaging/RENAMED_SKILLS.md` lists them and how to restore them.
- `build/config/flavors/boc/packs/` — the resource packs (folk, biomes, flora, fauna, ores, compendium, aether, world). Go here for anything from the Book of Cities, the Compendium, the Aether Library or CRUCIBLE.
- `build/specs/` — the 17 docs (tutorials, how-tos, reference, explanation with ADR-001 to ADR-021). Go here before modifying architecture.
- `build/ui/` — the workbench, the Pocket and Goblin Grounds, built, plus their sources. Go here to open or republish a page.
- `build/config/` — type files, flavors, the floor, the plugin manifest. Go here to see or copy a role, clan, mount or city.
- `build/assets/` — the build record and the gallery images. Go here to see what the engine makes.
- `dependencies/DEPENDENCY_MAP.md` — the module tree. Go here before any change, to see what it affects.
- `codex/mini-indexes/` — one page per module: what it is, key contents, what it is not.
- `pretune/` — twelve scenarios with expected pixel hashes. Go here to prove the engine still makes the same goblins, folk, packs and worlds.

### For Status and History
- `codex/CHANGELOG.md` — the FORGE entry. Go here when version context matters.
- `codex/OPEN_QUESTIONS.md` — what is unresolved. Go here before deciding something that may already be open.
- `codex/TAG_REGISTRY.md` — every tag and what carries it.

### For Post-Build Additions
- `updates/UPDATE_INDEX.md` — everything added after the forge. Go here before a Companion Builder session.

## Current State

### Built and Working
- Engine v0u1p0 — 24 of 24 build gates, 32 of 32 plan gates, 51 of 51 mutations caught, from-empty passes.
- Characters — 29 goblin jobs, 10 subspecies, 7 clans, 2 mounts, 9 expressions, six tiers, four eras, signatures at 8 px.
- Views — ten named views plus any turn and tilt, from one lifted model; walk in side view; 8-direction turnarounds.
- Cities — Goblintown from 35 names; any names file works.
- Resource packs — 316 types in 8 packs from the Book of Cities, the Compendium, the Aether Library and CRUCIBLE; folk and traits stack on any job.
- Goblin Grounds — playable page and `pixelgoblin sandbox` export, planned identically in both languages.
- Workbench, Pocket and Goblin Grounds — offline pages, JavaScript pixel-identical to Python.
- Plugin — three skills and nine MCP tools, tested from the packaged file.
- VI Builder — registration profile and process_record ready for its registry.

### In Progress
- Nothing mid-build. The next work is chosen by Mark (see Next Action).

### Open / Unresolved
- Side and top views are inferred, not art-directed; small 3D views look blocky — see OPEN_QUESTIONS Q1, Q2.
- 103 goldens changed on purpose in session 4 and await Mark as witness — Q6.
- Pack colours are mostly inferred from names until Mark sets canonical palettes — Q13.
- 16 SLM-e pieces await SLM-e's validator — Q7.
- The Vanilla Core composite-run patch awaits Mark — Q8.

### Next Action
- Mark looks at the gallery and re-blesses the session 4 goldens with his name as witness; then pick the next feature (pose as data is recommended).

## Key Vocabulary

| Term | Meaning |
|---|---|
| type file | A TOML file (integers only) that describes what to generate: a role, species, mount, clan table, city, scene, tile set |
| seed / name seed | A whole number, or a name hashed to one; same type file + same seed = same bytes |
| tier | Pixel resolution: 8, 16, 32, 64, 128 or 256 px |
| era | The look of a console generation: 8-bit (3 colours), 16-bit (15), 32-bit (31), hd (255) |
| genome | The tier-independent character; drawn, never stored per tier |
| LOD ladder / rung | The smallest tier at which each feature is drawn |
| build bit chain | One character at every tier, side by side (`card`, `chain`) |
| signature | The one feature that says who a role is, promoted to the 8 px rung |
| lift | Turning the front drawing into solids, so every view comes from one model |
| decal | A face, brow or pattern painted on the front half of a solid |
| role / subspecies / overlay | A job file that extends the species; a variant (snow, cave) whose own keys are laid over the role |
| clan (team) | Clothes colours only; the type hash stays the role's own |
| mount / beast | War boar or warg, built as solids in a cube twice the goblin's |
| census / household | Who each name becomes; people sharing a surname |
| flavor / vanilla | Book of Cities content (Proprietary) vs the CC0 vanilla pack; the scrub keeps them apart |
| gate / plan gate | B00–B21 build checks; G01–G30 exit criteria |
| mutation / falsify | A deliberate break a gate must catch |
| golden / re-bless | A stored pixel hash; changed only with Mark as witness |
| ratchet / FLOOR | Counts that may only go up |
| parity | JavaScript pixels equal Python pixels |
| workbench / pocket | The full browser editor / the quick maker widget |
| VUP | Mark's version format: vMAJORuMINORpPATCH (v0u1p0) |
| folk | a Book of Cities race as an overlay (`boc.race.sub.dwarf`); any job can be any folk |
| trait | a Compendium axis as an overlay (`boc.trait.sub.axis_frost`), stacked after a folk |
| overlay stack | overlays applied left to right: `--sub dwarf,axis_flame` |
| stature | a folk's height relative to a goblin (percent, capped by the canvas) |
| resource pack | a generated folder of type files with a `pack.toml` manifest and its source catalog |
| grounded / category_default / intentionally_ungrounded | where an ore's density came from: CRUCIBLE, a typical value, or deliberately none (fantasy) |
| soul / supplement | an Aether Library identity; a PixelGoblin avatar is offered beside it, never over it |
| Goblin Grounds | the sandbox and minigame area; a world is its biome and seed |

Do not substitute these terms with generic equivalents. See `codex/TAG_REGISTRY.md` for the full tag vocabulary.

## CALS Namespace

This project has a CALS namespace defined in `codex/CALS_NAMESPACE.md`.

The namespace covers: how a request routes between the deterministic core (generators, rig, lift, city), the checking layer (gates, verdicts, hazards), the access layer (widget, workbench, plugin, capsule) and the designed-but-unbuilt optional model slot, including the rule that nothing leaves the core without being re-quantised. Load CALS_NAMESPACE.md when: deciding where a feature belongs, whether something may use a model, or which surface to hand Mark.

This namespace is closed. It does not extend or reference CALS namespaces from other projects.

## Post-Build Additions

Companion Builder sessions: 0

Last addition: none

For full list: see `updates/UPDATE_INDEX.md`

---
—Shibbieness
—Claude
