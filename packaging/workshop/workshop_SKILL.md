---
name: pixelgoblin-workshop
description: "PixelGoblin Workshop is the working, uploadable capsule for Shibbieness's deterministic pixel-art engine: one name makes the same goblin at every size from 8 to 256 px, from any side, as any folk of the Book of Cities, in clan colours, on a mount, in a town built from names, or walking a Goblin Grounds world whose ores weigh what CRUCIBLE says. Load this skill when PixelGoblin, its goblins or folk, tiers, views, mounts, clans, cities, resource packs, Goblin Grounds, the Workbench, the Pocket, the plugin, its gates, or changing and re-forging PixelGoblin comes up. With it loaded, Claude can unpack and run the whole engine, change it under its gates, re-forge the next version, and look anything up in the original pixelgoblin-pseudoskill capsule, which is kept inside unchanged."
metadata:
  version: "v1u0p1"
  version_format: "VUP"
  author: "Shibbieness (Mark)"
  co_author: "Claude"
  organization: "M MAOU LLC"
  forged: "2026-09-27"
  patched: "2026-09-29"
  build_mode: "compound"
  immutable_core: "true"
  update_structure_version: "1.0"
  built_using: "pseudoskills-builder (Compound Build mode, dense-session protocol)"
  lineage: "descends from pixelgoblin-pseudoskill v1u0p1, archived unchanged in archive/"
  composes_with: "spire, slm-e, book-of-cities, book-of-cities-compendium-builder, aether-library-pseudoskill, crucible, vi-builder, gilwright, dropzone, cals, working-with-mark, eexpand"
  companions: "the pixelgoblin plugin (build/assets/pixelgoblin.plugin), working-with-mark (operational pairing)"
---

> ⚠️ IMMUTABILITY NOTICE
>
> This capsule, as uploaded, is read-only. Its core files, documentation, code,
> dependencies, and index structures are not edited in place by the Project Codex
> Compiler or the Companion Builder mode. These tools create; they do not edit.
>
> To add new artifacts (companions, guides, tests, documentation): use Companion Builder mode.
> New additions index into the updates/ layer only.
>
> This is the workshop, so improving it is expected. The way to change it is to re-forge it:
> unpack the source, change it, pass the gates, then `python3 tools/package.py workshop`
> makes the next version (VUP bump), which replaces this one on upload.
> The original capsule in `archive/` is never changed by anything.
>
> This notice is a feature, not a warning. The constraint is the trustworthiness.

# PixelGoblin Workshop

The ideas are his. Claude is the translator.

**State on load:** this file is the doorway; `PseudoSKILL.md` is the room. The whole project is packed as one file, `build/source/pixelgoblin-src.zip`, so the capsule stays under the 200-file upload limit. Unpack it to run or change anything:

```
python3 build/source/workshop.py unpack /tmp/pg
cd /tmp/pg && python3 -m pixelgoblin --help
```

In these docs, **`src:path`** means that path inside the source bundle (for example `src:pixelgoblin/gen/rig.py`). After unpacking it is just `path`.

## Project Identity

| Field | Value |
|---|---|
| Project Name | PixelGoblin |
| Short Name | PG |
| Capsule | pixelgoblin-workshop (the working capsule) |
| Author | Shibbieness (Mark) |
| Organization | M MAOU LLC |
| Current Status | Active |
| Version | engine v0u1p0 · workshop v1u0p1 (patch of v1u0p0) |
| Forged | 2026-09-27 |
| Lineage | pixelgoblin-pseudoskill v1u0p1, kept unchanged in `archive/` |
| CALS Namespace | Yes |
| Build Present | Yes (complete, runnable, gated, in one bundle) |

## What This Project Is

PixelGoblin makes pixel art three ways from one small engine: it **generates** sprites from a type file plus a seed, **converts** any image into pixel art that fits a tag, and **learns** a type file from one example. It also builds autotile sets, seamless textures, parallax backdrops, UI kits, villages and Warren dungeons. The same type file and seed make the same bytes in every process, in Python and in the browser.

Its heart is the goblin **rig**. A character is one **genome** that never sees the **tier**; it is drawn at 8, 16, 32, 64, 128 and 256 px, each tier adding features, each with an **era** look (8-bit, 16-bit, 32-bit, HD). A **name is a seed**, so Grubnak is always Grubnak. The front drawing is **lifted** into one 3D model, so every view (side, back, isometric, top, any turn and tilt) shows the same goblin. Goblins wear **clan** colours, ride **mounts**, show nine **expressions**, and a list of names becomes a **city** of households.

The **resource packs** bring Mark's other worlds in as data: 37 **folk** of the Book of Cities, 9 biomes, 165 plants, fungi, animals and fish, 60 ores **grounded** in CRUCIBLE, the Compendium's ranks and **traits**, and the Aether Library's **souls** (avatars are **supplements**, never overwrites). **Goblin Grounds** is the sandbox and minigame that uses them.

It is built under SPIRE's discipline: 24 build gates (B00 to B23), 51 mutations that must all be caught, 224 goldens, a count ratchet and a from-empty run. Standard-library Python with an integer-only runtime; the browser pages are proved pixel-identical.

**Why a workshop:** the original capsule (`pixelgoblin-pseudoskill`) holds 1,058 files and cannot be uploaded (the limit is 200). It is kept here byte-for-byte as the frozen reference. This workshop is the same project in an uploadable shape, and the one to improve.

## Navigation Map

### Start Here
- `PseudoSKILL.md` — the full operational reference: contracts, architecture, workflows, rules. Go here for anything this router does not answer.
- `codex/MASTER_INDEX.md` — every indexed item with tags, plus a concept-to-item table. Go here first for any lookup.
- `codex/LINEAGE.md` — where this came from: the original capsule, the session it was built in, the published pages, and how to look things up in each. Go here when something seems missing.
- `codex/NARRATIVE.md` — the story of sessions 1 to 5 and why things are the way they are.
- `codex/CALS_NAMESPACE.md` — how work routes between the engine's parts, the gates and the optional model slot.

### For Technical Work
- `build/source/pixelgoblin-src.zip` — the complete repository, runnable once unpacked. Every `src:` path lives here.
- `build/source/workshop.py` — the helper: `unpack DIR`, `original [PATH]`, `find WORDS`, `check`.
- `build/ui/` — the Workbench, the Pocket and Goblin Grounds, built and self-contained. Go here to open or republish a page.
- `build/specs/` — the project's docs (tutorials, how-tos, reference, explanation with the ADRs). Go here before changing architecture.
- `build/config/` — the floor, the flavor manifest and the plugin manifest; the type files themselves are `src:types/` and `src:flavors/`.
- `build/assets/` — `pixelgoblin.plugin`, ready to install for the nine drawing tools.
- `archive/` — the original capsule, unchanged. Read it with `workshop.py original`.
- `dependencies/DEPENDENCY_MAP.md` — the module tree. Go here before any change.
- `codex/mini-indexes/` — one page per module: what it is, key contents, what it is not.
- `pretune/` — twelve scenarios with expected pixel hashes, to prove the engine still makes the same pictures.

### For Status and History
- `codex/CHANGELOG.md` — the FORGE entry and its lineage.
- `codex/OPEN_QUESTIONS.md` — what is unresolved.
- `codex/TAG_REGISTRY.md` — every tag and what carries it.

### For Post-Build Additions
- `updates/UPDATE_INDEX.md` — everything added after the forge.

## Current State

### Built and Working
- Engine v0u1p0 — 24 of 24 build gates, 51 of 51 mutations caught, from-empty passes.
- Characters, views, mounts, clans, cities, resource packs, Goblin Grounds, three pages, the plugin: all as in the original capsule.
- This workshop — 1 SKILL.md, well under 200 files, passes the Forge checklist and the skill upload checker.

### Open / Unresolved
- Side and top views are inferred; small 3D views look blocky — OPEN_QUESTIONS Q1, Q2.
- 103 goldens from session 4 await Mark as witness — Q6.
- Pack colours are mostly inferred from names — Q13.
- Keeping the workshop under the file limit as it grows — Q18.

### Next Action
- Mark looks at the gallery and re-blesses the session 4 goldens; then picks the next feature (pose as data is recommended).

## Key Vocabulary

| Term | Meaning |
|---|---|
| type file | A small TOML file of integers that describes a thing to generate |
| tier | A size rung: 8, 16, 32, 64, 128 or 256 px |
| era | A look (8-bit, 16-bit, 32-bit, HD), separate from size |
| genome | The tier-free description of one character |
| signature | A role's defining feature, readable even at 8 px |
| lift | Turning the front drawing into 3D solids so every view agrees |
| clan | A colour team (ashfang, duskveil, ...) that changes cloth only |
| folk / trait | Overlays from the Book of Cities and the Compendium, stacked on any job |
| grounded | An ore whose weight comes from CRUCIBLE's real density |
| supplement | An Aether Library avatar: added beside a soul, never replacing it |
| gate / mutation | A check, and a deliberate break that proves the check notices |
| golden | A stored pixel hash that a picture must keep matching |
| workshop | This capsule: the uploadable, improvable form of the project |
| original | `pixelgoblin-pseudoskill` v1u0p1, frozen in `archive/` |
| `src:` | A path inside `build/source/pixelgoblin-src.zip` |

## CALS Namespace

Namespace `pixelgoblin`, closed. Components: **Generators**, **Rig** and **Lift** (synthesis that keeps identity across sizes and views), **City** (population from names), **Convert** and **Likeness** (reduction and learning), **Verdicts** (assessment, never production), **Gates** (verification of the whole), the **Pages** and **Plugin** (direct and conversational access), an **optional model slot** (planned, never in the core), and the **Workshop** (re-forging one version at a time, the original untouched). Routing: a name goes to the Rig, an angle to the Lift, a town to the City, "is it right?" to the Verdicts, any change through the Gates. Full namespace: `codex/CALS_NAMESPACE.md`.

## Post-Build Additions

Companion Builder sessions: 0
Last addition: none
For the full list: `updates/UPDATE_INDEX.md`

—Shibbieness
—Claude
