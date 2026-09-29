#!/usr/bin/env python3
"""Forge the PixelGoblin PseudoSkill capsule (pixelgoblin-pseudoskill.skill).

Follows the PseudoSkills Builder output spec (Project Codex Output Spec):
SKILL.md, PseudoSKILL.md, META.json, codex/, dependencies/, build/, pretune/,
updates/. Hand-written prose lives in packaging/capsule/. Everything that can
drift (indexes, tags, dependency graph, changelog, pretune expectations, copies
of the build) is generated here from one item table and checked by validate(),
which is the Forge validation checklist as code. Nothing is packaged that fails it.

    —Shibbieness
    —Claude
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NAME = "pixelgoblin-pseudoskill"
CAPSULE_VERSION = "v1u0p0"      # VUP; equals codex 1.0.0 in the spec's semver
FORGED = "2026-09-26"
PATCH_VERSION = "v1u0p1"  # upload compatibility (see the changelog CORRECTION entry)
# A skill upload accepts exactly one SKILL.md. The repository's own skill files are
# renamed <name>_SKILL.md inside build/source/ only; `restore` puts them back.
RENAMED_SKILLS = [
    ("packaging/capsule/SKILL.md", "packaging/capsule/capsule_SKILL.md"),
    ("packaging/plugin/skills/pixelgoblin/SKILL.md", "packaging/plugin/skills/pixelgoblin/pixelgoblin_SKILL.md"),
    ("packaging/plugin/skills/pixelgoblin-types/SKILL.md", "packaging/plugin/skills/pixelgoblin-types/pixelgoblin-types_SKILL.md"),
    ("packaging/plugin/skills/pixelgoblin-engine/SKILL.md", "packaging/plugin/skills/pixelgoblin-engine/pixelgoblin-engine_SKILL.md"),
]
SESSION = "5"

# ---------------------------------------------------------------- tags
STRUCTURAL = {
    "#source": "Core source code files", "#ui": "UI pages and their sources", "#spec": "Technical specifications and docs",
    "#config": "Type files, flavor manifests, floors", "#asset": "Images and generated records", "#test": "Gates, mutations, goldens, pretune",
    "#index": "Index files", "#narrative": "Story and decision history", "#changelog": "Version history",
    "#registry": "Tag and piece registries", "#cals": "CALS namespace", "#open-questions": "Unresolved decisions",
    "#dependency-map": "Dependency declarations", "#module": "A discrete component that is not engine source (plugin, patches)",
    "#build-guide": "Step-by-step procedures", "#gameplan": "Plans and roadmaps",
    "#companion": "Companion documents (update slots)", "#api-ref": "API references (update slots)", "#misc": "Items that fit no category (update slots)",
}
STATUS = {
    "#complete": "Finished, gated and stable", "#active": "In use and still growing", "#draft": "Exists, not finalised",
    "#open": "Unresolved; action pending", "#planned": "On the roadmap, not built", "#blocked": "Cannot proceed without an outside step",
}
NARRATIVE = {
    "#origin": ("the founding design", "Session 1: the design document, ADR-001 to ADR-008"),
    "#v1-design": ("the first build", "Session 2: engine, CLI, editor, gates, Vanilla Core flavor"),
    "#naming": ("canon-establishing names", "PixelGoblin, type file, tier, era, rung, flavor"),
    "#pivot": ("a change of direction", "Python before Rust (ADR-009); HTML editor instead of egui (ADR-011)"),
    "#validated": ("tested and confirmed", "anything proved by a gate and its mutation"),
    "#rejected": ("considered and not chosen", "carving views from drawings; float geometry; a second 3D character system"),
    "#revision": ("a formal rethink", "the three-legs fix; signatures at 8 px; the decal layer rule"),
    "#milestone": ("a release point", "v0u1p0 gated builds at the end of each session"),
    "#open-question": ("unresolved, part of the active story", "codex/OPEN_QUESTIONS.md Q1 to Q12"),
    "#session:1": ("Session 1", "design"), "#session:2": ("Session 2", "name, build, SPIRE discipline, licensing"),
    "#session:3": ("Session 3", "goblin roster, tiers and eras, build bit chains, village"),
    "#session:4": ("Session 4", "views from any side, mounts, clans, expressions, zoom, cities"),
    "#session:5": ("Session 5", "widget, plugin, this capsule, resource packs, Goblin Grounds, VI Builder registration"),
}
PROJECT_TAGS = {  # project-specific, all narrative type
    "#determinism": "the same inputs give the same bytes on every platform",
    "#tier-chain": "one genome drawn at 8 to 256 px, each tier adding features",
    "#views": "every view is a projection of one lifted model",
    "#city": "a population from a list of names",
    "#parity": "JavaScript reproduces Python pixel for pixel",
    "#flavor": "Book of Cities content kept apart from the vanilla pack",
    "#spire-discipline": "gates, mutations, ratchets and from-empty runs",
    "#access": "reaching PixelGoblin from chats: widget, plugin, capsule",
    "#packs": "resource packs drawn from the Book of Cities, the Compendium, the Aether Library and CRUCIBLE",
    "#grounds": "Goblin Grounds, the sandbox and minigame area",
}

# ---------------------------------------------------------------- items
# id, label, capsule path, structural, status, narrative tags, depends-on ids, what, key contents, navigation notes, what it is not
ITEMS = [
    dict(id="core-engine", label="Core engine", path="build/source/pixelgoblin/rng.py", st="#source", ss="#complete", nt=["#v1-design", "#determinism"],
         deps=[], what="The integer-only foundation: xoshiro128** random streams named by path (so adding a part never shifts another), sprites with indexed palettes, a hand-written PNG encoder and decoder, OKLab colour, palettes, exports (sheets, ASCII longevity export, Aseprite-style JSON) and 19-byte share codes with a typo check.",
         keys=[("rng.py", "xoshiro128**, derive(), named Streams", "pixelgoblin/rng.py"), ("sprite.py", "Sprite, blit, pixel_hash", "pixelgoblin/sprite.py"),
               ("png.py", "stdlib PNG read/write", "pixelgoblin/png.py"), ("color.py, palettes.py", "OKLab, ramps", "pixelgoblin/"),
               ("export.py", "contact sheets, strips, ASCII", "pixelgoblin/export.py"), ("sharecode.py", "PG- share codes", "pixelgoblin/sharecode.py")],
         nav="Read rng.py first: every other module draws randomness from named streams. The reference vector in gate B01 is the contract.",
         not_="Not the character system (see rig) and not the type-file schema (see typefile)."),
    dict(id="typefile", label="Type files and validation", path="build/source/pixelgoblin/typefile.py", st="#source", ss="#complete", nt=["#v1-design", "#naming"],
         deps=["core-engine"], what="Loads, merges (extends, _add), composes (subspecies overlays), validates and hashes type files. Every refusal is one plain-English sentence naming the field. Decimal numbers are refused anywhere. Also clans (with_team keeps the type hash), items written as data, signatures and beast validation.",
         keys=[("load / compose / with_team", "reading and combining type files", "typefile.py"), ("validate", "plain-English refusals with suggestions", "typefile.py"),
               ("type_hash", "SHA-256 of canonical JSON", "typefile.py"), ("search_path", "types/vanilla then flavors/", "typefile.py")],
         nav="Start at load() and validate(). The canonical-hash rules are in docs/explanation/determinism.md.",
         not_="Not the field reference; that is build/specs/reference/type-files.md."),
    dict(id="generators-2d", label="2D generators (mask, L-system, parallax)", path="build/source/pixelgoblin/gen/mask.py", st="#source", ss="#complete", nt=["#v1-design"],
         deps=["core-engine", "typefile"], what="The first generators: template masks for creatures, items and icons; L-system plants; parallax backdrops. Each is a pure function of a type file and a seed.",
         keys=[("mask.py", "templates, mirrored halves, parts by chance", "gen/mask.py"), ("lsystem.py", "trees and shrubs", "gen/lsystem.py"), ("parallax.py", "layered backdrops", "gen/parallax.py"), ("gen/__init__.py", "the generator registry", "gen/__init__.py")],
         nav="gen/__init__.py lists every generator; frames(tf, seed) is the entry point.",
         not_="Not characters (rig) or scenes (scene)."),
    dict(id="tiles", label="Tiles: autotile and WFC", path="build/source/pixelgoblin/tiles/autotile.py", st="#source", ss="#complete", nt=["#v1-design"],
         deps=["core-engine", "typefile"], what="The 47-tile blob autotile set from a terrain type file, and Wave Function Collapse for seamless textures from a small sample, which always returns an image.",
         keys=[("autotile.py", "256 masks reduced to 47 by the diagonal rule", "tiles/autotile.py"), ("wfc.py", "2x2 patterns, fallback counted", "tiles/wfc.py")],
         nav="Gate B04 holds the tile contracts.", not_="Not the UI kit (uikit)."),
    dict(id="convert", label="Convert, likeness, verdicts, hazards, readability", path="build/source/pixelgoblin/convert.py", st="#source", ss="#complete", nt=["#v1-design", "#validated"],
         deps=["core-engine", "typefile"], what="Turns any image into pixel art under a tag's profile (own k-means in OKLab, pixel-perfect cleanup), learns a type file from one example (likeness), gives two separate verdicts (spec and target, never merged), reports flashing and licence hazards in mechanism order, and measures readability at 1x (squint).",
         keys=[("convert.py", "convert_rgba, pixel_perfect, likeness", "convert.py"), ("verdicts.py", "spec vs target", "verdicts.py"), ("hazard.py", "flash and licence hazards", "hazard.py"), ("readability.py", "squint", "readability.py")],
         nav="Tag profiles live in build/source/types/tags.toml.", not_="Not a model; there is no ML anywhere (ADR-003)."),
    dict(id="uikit", label="UI kit (GUI slots)", path="build/source/pixelgoblin/uikit.py", st="#source", ss="#complete", nt=["#v1-design"],
         deps=["core-engine", "typefile"], what="9-slice panels, four distinct button states and icons for games and apps, with unbroken outlines at five sizes.",
         keys=[("uikit.py", "build_kit", "uikit.py")], nav="Gate B06.", not_="Not the workbench's own interface."),
    dict(id="rig", label="Character rig (2D, tiers, eras)", path="build/source/pixelgoblin/gen/rig.py", st="#source", ss="#complete", nt=["#session:3", "#tier-chain", "#revision"],
         deps=["core-engine", "typefile"], what="A character is one genome that never sees the tier, drawn at 8, 16, 32, 64, 128 and 256 px. Each tier adds features on the LOD ladder; each size has an era look (8-bit 3 colours, 16-bit 15, 32-bit 31, HD 255). Role signatures are promoted to the 8 px rung and snapped so every job reads at 8 px; eyes and signatures keep their colours when eras reduce. Expressions, poses, items written as data, clans and zoom plans live here.",
         keys=[("genome()", "the tier-independent character", "gen/rig.py"), ("render() = visible_shapes + shade_index + finish", "drawing at one tier", "gen/rig.py"),
               ("LOD, TIER_HEAD, TIER_EYE, ERAS, DEFAULT_CHAIN", "the tier chain tables", "gen/rig.py"), ("signature()", "the 8 px identity", "gen/rig.py"),
               ("_era_reduce", "colour reduction with heavy colours", "gen/rig.py"), ("zoom_plan", "crowd-to-portrait sizes", "gen/rig.py")],
         nav="Read docs/explanation/tier-chain.md first. This file is transpiled to JavaScript: keep to the transpiler's subset.",
         not_="Not the side, back or top views (rig3d)."),
    dict(id="rig3d", label="Views from any side (rig3d)", path="build/source/pixelgoblin/gen/rig3d.py", st="#source", ss="#complete", nt=["#session:4", "#views", "#validated"],
         deps=["rig"], what="Lifts the front drawing into one model of solids (ellipsoids, capsules, pills, wraps, slabs, domes), voxelises it and ray-marches it with an integer camera. Ten named views plus any turn and tilt; decals (faces, brows, patterns) paint the front half. Front, side and top agree like a draughtsman's projections.",
         keys=[("lift()", "2D shapes to solids and decals", "gen/rig3d.py"), ("voxelize / trace / paint", "the integer renderer", "gen/rig3d.py"),
               ("VIEWS, TURNAROUND", "named cameras", "gen/rig3d.py"), ("render_view()", "the public entry", "gen/rig3d.py"), ("views_agree()", "the orthographic check", "gen/rig3d.py")],
         nav="docs/explanation/views.md has the depth-rule table. ADR-018 explains why lifting beat carving.",
         not_="Not hand-drawn side views; they are inferred (see OPEN_QUESTIONS Q1)."),
    dict(id="beast", label="Mounts and riders (beast)", path="build/source/pixelgoblin/gen/beast.py", st="#source", ss="#complete", nt=["#session:4", "#views"],
         deps=["rig3d", "rig"], what="War boar and warg built as 3D solids from the start, in a cube twice the goblin's, so a rider sits at the same scale. seat_rider re-poses the legs astride.",
         keys=[("genome / beast_solids", "the beast", "gen/beast.py"), ("mounted()", "rider plus mount from any view", "gen/beast.py")],
         nav="ADR-020.", not_="Not a general creature system; two mount kinds only."),
    dict(id="scene-warren", label="Scenes, villages and Warren dungeons", path="build/source/pixelgoblin/gen/scene.py", st="#source", ss="#complete", nt=["#session:3", "#flavor"],
         deps=["rig", "typefile"], what="The village composer places real characters from their role files in crowd bands, with huts and stalls whose detail grows with size (PROP_LOD). Warren builds dungeons in which every room can be reached.",
         keys=[("scene.py", "sceneFrames, crowd bands, props", "gen/scene.py"), ("warren.py", "rooms, reachability", "gen/warren.py")],
         nav="Scene ids: boc.scene.village and boc.scene.village.hd.", not_="Not the city census (city)."),
    dict(id="city", label="Cities from names", path="build/source/pixelgoblin/city.py", st="#source", ss="#complete", nt=["#session:4", "#city"],
         deps=["rig", "scene-warren", "typefile"], what="A names file becomes a census: each citizen's job and look come from the city hash plus their own name, so adding or removing a citizen changes nobody else. Surnames form households; children inherit face, hair and build; a surname that is a clan name joins that clan; the village holds as many as its bands allow.",
         keys=[("parse_names / census", "who is who", "city.py"), ("village()", "the town with its people", "city.py"), ("INHERITED", "what children take from parents", "city.py")],
         nav="docs/howto/build-a-city.md; ADR-019.", not_="Not a simulation of daily life (planned)."),
    dict(id="outputs", label="Cards, brood, GIFs, font", path="build/source/pixelgoblin/cards.py", st="#source", ss="#complete", nt=["#session:3"],
         deps=["rig", "core-engine"], what="Character cards (every tier with what each adds), expression sheets, clan rows, zoom frames, brood (a child that inherits from both parents), family trees, animated GIFs with the flash-hazard check, and the small pixel font used on sheets.",
         keys=[("cards.py", "card, labelled, expressions, team_row, zoom", "cards.py"), ("brood.py", "brood, family", "brood.py"), ("gif.py", "GIF writer", "gif.py"), ("font.py", "sheet labels", "font.py")],
         nav="These are what the CLI's card, expressions, clans, zoom, gif and family commands call.", not_="Not generators."),
    dict(id="cli", label="Command line and Vanilla Core flavor", path="build/source/pixelgoblin/cli.py", st="#source", ss="#complete", nt=["#v1-design", "#milestone"],
         deps=["core-engine", "typefile", "generators-2d", "tiles", "convert", "uikit", "rig", "rig3d", "beast", "scene-warren", "city", "outputs"],
         what="32 commands, each with help and an example (gate B14 derives docs/reference/cli.md from the parser). vanilla_flavor.py and flavor.toml make PixelGoblin a Vanilla Core flavor with 8 capabilities.",
         keys=[("build_parser / EXAMPLES", "every command", "cli.py"), ("main()", "entry point: python3 -m pixelgoblin", "cli.py"), ("vanilla_flavor.py", "the flavor contract", "vanilla_flavor.py")],
         nav="build/specs/reference/cli.md is generated from this file.", not_="Not the MCP server (plugin)."),
    dict(id="transpiler-js", label="JavaScript core and transpiler", path="build/source/tools/transpile_rig.py", st="#source", ss="#complete", nt=["#session:3", "#parity"],
         deps=["rig", "rig3d", "beast"], what="rig.py, rig3d.py and beast.py are transpiled to editor/pg-rig.gen.js, so the browser draws the same pixels. pg-core.js holds the hand-ported core; pg-rig.js the rest. Gate B13 checks 306 parity cases.",
         keys=[("transpile_rig.py", "Python subset to JS", "tools/"), ("pg-core.js", "core in JS", "editor/"), ("pg-rig.js", "rig glue, city, scenes", "editor/"), ("pg-rig.gen.js", "generated geometry, do not edit", "editor/")],
         nav="Write `g.get(k, None) is not None`, never `k in g`; split tuple constants. ADR-017.", not_="Not a general Python-to-JS compiler."),
    dict(id="workbench", label="Workbench (browser editor)", path="build/ui/pixelgoblin.html", st="#ui", ss="#complete", nt=["#v1-design", "#parity"],
         deps=["transpiler-js", "type-files"], what="One offline HTML page with the exact engine embedded: Generate, Brood, Characters (views, rotate, clans, mounts, expressions, zoom), Village, City, Backdrops, Tiles, UI kit and a type-file Editor.",
         keys=[("src.html", "source", "build/source/editor/src.html"), ("pixelgoblin.html", "built page", "build/ui/")],
         nav="Built by tools/build_editor.py. Published privately for Mark at https://claude.ai/artifact/EcDDXExxyk7zWFWsLFeZjS.", not_="Not the quick maker (pocket-widget)."),
    dict(id="pocket-widget", label="PixelGoblin Pocket (widget)", path="build/ui/pixelgoblin-pocket.html", st="#ui", ss="#complete", nt=["#session:5", "#access"],
         deps=["transpiler-js", "type-files"], what="A small page for any chat: type a name, pick a job, clan, mount, size and era; turn the goblin by dragging; see the whole size chain; save a picture or 8 directions; copy a share code (pg1/...) that brings the same goblin back.",
         keys=[("widget.src.html", "source", "build/source/editor/widget.src.html"), ("pixelgoblin-pocket.html", "built page", "build/ui/")],
         nav="Published privately for Mark at https://claude.ai/artifact/HRTVjLVPeRsQrRsMHbupqc.", not_="Not the full workbench."),
    dict(id="plugin", label="PixelGoblin plugin", path="build/source/packaging/plugin/.claude-plugin/plugin.json", st="#module", ss="#complete", nt=["#session:5", "#access"],
         deps=["cli", "workbench", "pocket-widget", "grounds-page"], what="A Claude plugin with three skills (pixelgoblin, pixelgoblin-types, pixelgoblin-engine), a standard-library MCP server with nine tools that return pictures inline (characters, sheets, cities, packs, avatars, sandbox worlds, list, any command, self-test), the bundled engine with every resource pack, and all three pages.",
         keys=[("plugin.json", "manifest", ".claude-plugin/"), (".mcp.json", "the server", "packaging/plugin/"), ("server/pixelgoblin_mcp.py", "nine tools", "packaging/plugin/server/"), ("skills/", "three skills; in this capsule each SKILL.md is renamed <name>_SKILL.md", "packaging/plugin/skills/")],
         nav="Built by tools/package.py into dist/pixelgoblin.plugin; gate B21 checks it. Inside this capsule the three skill files are pixelgoblin_SKILL.md, pixelgoblin-types_SKILL.md and pixelgoblin-engine_SKILL.md (build/source/packaging/RENAMED_SKILLS.md); run `tools/packaging_capsule.py restore` on a copied-out build/source before building the plugin.", not_="Not this capsule; the capsule is the project's memory, the plugin is the tool."),
    dict(id="gates", label="Gates, mutations, goldens, floor", path="build/source/tests/gate.py", st="#test", ss="#complete", nt=["#spire-discipline", "#validated"],
         deps=["cli", "transpiler-js", "plugin"], what="24 build gates (B00 to B23) cover plan gates G01 to G32. falsify.py breaks each behaviour a gate depends on and proves the gate notices. 224 goldens, a count ratchet (FLOOR.json), a from-empty run, and BUILD_STATUS.md written only after a full run.",
         keys=[("gate.py", "B00-B23", "tests/"), ("falsify.py", "mutations", "tests/"), ("FLOOR.json", "the ratchet", "tests/"), ("golden/goldens.json", "224 pixel hashes", "tests/golden/")],
         nav="Run `PYTHONHASHSEED=0 python3 tests/gate.py --all` then `python3 tests/falsify.py`.", not_="Not the pretune scenarios (pretune/), which are for trying variations."),
    dict(id="type-files", label="Type files and flavors", path="build/config/flavors", st="#config", ss="#active", nt=["#flavor", "#session:3"],
         deps=["typefile"], what="The vanilla pack (10 types, CC0 sprites) and the Book of Cities flavor (Proprietary): 29 goblin jobs, 10 subspecies, 2 mounts, 7 clans, Goblintown and its 35 names, the villages, the original goblin, aquatic goblin, glowcap and reef, plus the resource packs (see resource-packs).",
         keys=[("types/vanilla/", "vanilla pack", "build/config/types/"), ("types/tags.toml", "tag profiles", "build/config/types/"), ("flavors/boc/", "Book of Cities flavor", "build/config/flavors/"), ("FLOOR.json, flavor.toml", "floor and flavor manifest", "build/config/")],
         nav="Copies of build/source/types and build/source/flavors; the validator checks they are identical.", not_="Not code."),
    dict(id="specs", label="Documentation (Diátaxis)", path="build/specs/explanation/decisions.md", st="#spec", ss="#complete", nt=["#naming", "#milestone"],
         deps=[], what="19 pages: tutorials, how-tos (using PixelGoblin from Claude, the resource packs, Goblin Grounds), reference (CLI, type files) and explanation (determinism, gates, gameplan, decisions ADR-001 to ADR-023, stack, tier chain, views), plus the README.",
         keys=[("tutorials/", "first sprite, a species", "build/specs/"), ("howto/", "convert, game, UI kit, city", "build/specs/"), ("reference/", "cli.md, type-files.md", "build/specs/"), ("explanation/", "why", "build/specs/")],
         nav="decisions.md for why; gameplan.md for what is next; gates.md for how it is checked.", not_="Not the narrative of the sessions (codex/NARRATIVE.md)."),
    dict(id="build-record", label="Build record and gallery", path="build/assets/pixelgoblin-build-record.html", st="#asset", ss="#complete", nt=["#milestone", "#session:4"],
         deps=["specs"], what="The generated build record (every count computed, never typed) and the gallery images, remade from committed type files and seeds.",
         keys=[("pixelgoblin-build-record.html", "sessions 2 to 4 with gallery", "build/assets/"), ("gallery/*.png", "deterministic images", "build/assets/gallery/")],
         nav="Regenerate with tools/record_gallery.py and tools/build_record.py.", not_="Not Mark's reference images, which are never published."),
    dict(id="stack", label="Stack connections (SLM-e pieces, patches, QRen example)", path="build/source/slme/pieces.json", st="#registry", ss="#active", nt=["#session:2", "#session:4"],
         deps=["cli"], what="32 SLM-e pieces with degrades_to; the Vanilla Core composite-run patch for Mark to apply; the QRen round-trip example; CRUCIBLE ramp shaping; the leak guard.",
         keys=[("slme/pieces.json", "32 pieces (16 unvalidated)", "build/source/slme/"), ("patches/vanilla-core-composite-fix.patch", "for Vanilla Core", "build/source/patches/"),
               ("examples/composite_qren.py", "QRen archive round trip", "build/source/examples/"), ("tools/leakguard.py", "publication guard", "build/source/tools/")],
         nav="docs/explanation/stack.md is the full table of what connects and its status.", not_="Not the other projects themselves; they are read-only."),
    dict(id="resource-packs", label="Resource packs", path="build/config/flavors/boc/packs/races/pack.toml", st="#config", ss="#active", nt=["#session:5", "#packs"],
         deps=["typefile", "pack-builder"], what="Eight packs generated from Mark's own projects: 37 folk of the Book of Cities as overlays for any job, 9 biomes (sky and ground), 100 plants and fungi, 65 animals and fish, 60 ores grounded in CRUCIBLE (or honestly ungrounded), the Compendium's ranks and 14 trait overlays, the Aether Library's souls and Brackrun-Hollow, and the stations and districts as data.",
         keys=[("races/", "37 folk overlays (stature, ears, skin, eyes, beards, tusks, fins)", "flavors/boc/packs/"), ("biomes/", "sky + ground per biome, and who lives there", "flavors/boc/packs/"),
               ("flora/, fauna/", "165 plants, fungi, animals and fish", "flavors/boc/packs/"), ("ores/", "60 ores with a [crucible] table", "flavors/boc/packs/"),
               ("compendium/", "rank badges, trait overlays, catalog", "flavors/boc/packs/"), ("aether/", "souls.toml, Brackrun-Hollow, catalog", "flavors/boc/packs/"),
               ("sources/", "the JSON catalogs everything is generated from", "flavors/boc/packs/")],
         nav="`pixelgoblin packs` lists them; `pixelgoblin pack <name>` draws one. build/specs/howto/use-resource-packs.md explains overlays, grounding and avatars.",
         not_="Not hand-drawn art: most colours are inferred from names and flagged; the icons are generic body plans (see OPEN_QUESTIONS Q13, Q17)."),
    dict(id="pack-builder", label="Pack builder", path="build/source/tools/build_packs.py", st="#source", ss="#complete", nt=["#session:5", "#packs"],
         deps=["typefile"], what="Turns the source catalogs into type files: resolves colour words to ramps at tool time, builds folk and trait overlays, mask templates for fungi, animals and ores, L-system forms for plants, biome skies and grounds, and grounds every ore in CRUCIBLE's numbers. --check is what gate B22 runs.",
         keys=[("colour(), ramp()", "colour words to pixel-art ramps", "tools/build_packs.py"), ("race_overlay, trait_overlay", "overlays", "tools/build_packs.py"),
               ("ore_type", "CRUCIBLE grounding", "tools/build_packs.py"), ("aether_pack", "souls and Brackrun-Hollow", "tools/build_packs.py")],
         nav="Change a source catalog, then run the builder; never edit a generated pack file.", not_="Not an extractor: the catalogs were extracted once from the read-only skills."),
    dict(id="sandbox", label="Goblin Grounds engine (sandbox)", path="build/source/pixelgoblin/sandbox.py", st="#source", ss="#complete", nt=["#session:5", "#grounds"],
         deps=["core-engine", "typefile", "resource-packs"], what="Plans a world from a biome's residents and a seed: tiles, things to see and gather, a forge, a start and quests, with everything gatherable reachable. Weights come from the ores' CRUCIBLE tables; speed falls with load. plan_world is transpiled so the page plans the same world; export writes world.json, atlas.png and map.png.",
         keys=[("plan_world, reachable, quests, speed", "the transpiled planner", "pixelgoblin/sandbox.py"), ("world(), config_hash()", "a world's identity", "pixelgoblin/sandbox.py"),
               ("grams()", "weight and its source", "pixelgoblin/sandbox.py"), ("render(), export()", "files for game engines", "pixelgoblin/sandbox.py")],
         nav="build/specs/howto/play-goblin-grounds.md; ADR-023.", not_="Not a game engine: animals only wander in the page, and the forge smelts but has no recipes yet."),
    dict(id="grounds-page", label="Goblin Grounds (page)", path="build/ui/pixelgoblin-grounds.html", st="#ui", ss="#complete", nt=["#session:5", "#grounds", "#access"],
         deps=["sandbox", "transpiler-js", "resource-packs"], what="The playable sandbox: pick a biome, seed, name, job and folk; walk (keys, taps or a pad), gather, deliver quests at the forge, feel the weight; animals wander; Build mode places anything that lives there; Save world.json.",
         keys=[("grounds.src.html", "source", "build/source/editor/grounds.src.html"), ("pixelgoblin-grounds.html", "built page", "build/ui/")],
         nav="Published privately for Mark at https://claude.ai/artifact/UhFrDXaQNMqferxmQKQt1D.", not_="Not the workbench."),
    dict(id="vi-builder", label="VI Builder registration", path="build/source/packaging/vi-builder/REGISTRATION.md", st="#spec", ss="#draft", nt=["#session:5", "#access"],
         deps=["cli", "plugin"], what="How PixelGoblin enters VI Builder: as a Filesystem Source, and as two ML Processes (Tier 4a knowledge from the capsule; Tier 2b engine), with a LATTICE-style process_record whose query, status and shutdown endpoints map to real commands.",
         keys=[("REGISTRATION.md", "LEXIS-style profiles", "packaging/vi-builder/"), ("process_record.yaml", "BLOOM Stage 6 shape", "packaging/vi-builder/")],
         nav="VI Builder's own registry is not built yet; this is the proposal it can ingest.", not_="Not a running registration (see OPEN_QUESTIONS Q16)."),
    dict(id="packaging", label="Packaging tools", path="build/source/tools/package.py", st="#source", ss="#complete", nt=["#session:5", "#access"],
         deps=["plugin", "gates"], what="tools/package.py builds dist/pixelgoblin.plugin and, with tools/packaging_capsule.py, this capsule. The capsule's indexes, tags, graph, changelog and pretune expectations are generated from one table and checked by the Forge validation checklist as code.",
         keys=[("package.py", "plugin and capsule", "tools/"), ("packaging_capsule.py", "ITEMS table, build, validate()", "tools/")],
         nav="Run `python3 tools/package.py all`.", not_="Not a PseudoSkill Update Skill; it re-forges, it does not edit a capsule."),
]

# pretune scenarios: the questions a loaded capsule should be able to answer with pixels
SCENARIOS = [
    ("grubnak-iso", "Grubnak the blacksmith, isometric", ["view", "boc.goblin.blacksmith", "--name", "Grubnak", "--view", "iso_sw"]),
    ("mizzle-side-duskveil", "Mizzle the shaman from the side in Duskveil colours", ["view", "boc.goblin.shaman", "--name", "Mizzle", "--view", "side_right", "--team", "duskveil"]),
    ("brakka-turnaround", "Brakka the guard, 8 directions, tilted 30", ["turnaround", "boc.goblin.guard", "--name", "Brakka", "--pitch", "30"]),
    ("rider-warg-back", "A rider on a warg from behind", ["ride", "boc.goblin.rider", "boc.mount.wolf", "--seed", "2", "--view", "back", "--tier", "128"]),
    ("snow-miner-8bit", "A snow goblin miner in 8-bit at 32 px", ["view", "boc.goblin.miner", "--name", "Dig", "--sub", "snow", "--era", "8-bit", "--tier", "32"]),
    ("grubnak-card", "Grubnak's card, every size", ["card", "boc.goblin.blacksmith", "--name", "Grubnak"]),
    ("musician-expressions", "Nine faces of a musician", ["expressions", "boc.goblin.musician", "--seed", "4"]),
    ("goblintown", "Goblintown from its 35 names", ["city", "boc.city.goblintown", "flavors/boc/village/goblintown.names.txt"]),
    ("dwarf-smith-flame", "Thrain, a dwarf blacksmith with the flame trait, isometric", ["view", "boc.goblin.blacksmith", "--name", "Thrain", "--sub", "dwarf,axis_flame", "--view", "iso_sw"]),
    ("aelren-avatar", "Aelren of the Aether Library, as a supplement avatar", ["avatar", "Aelren", "--view", "iso_sw"]),
    ("ores-pack", "Every ore, grounded in CRUCIBLE", ["pack", "ores"]),
    ("mountain-grounds", "A Goblin Grounds world in the mountains", ["sandbox", "--biome", "mountain", "--seed", "3", "--size", "20x14"]),
]


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def _tags(it: dict) -> list[str]:
    return [it["st"], it["ss"]] + it["nt"]


def _rel(it: dict) -> list[str]:
    used_by = [o["id"] for o in ITEMS if it["id"] in o["deps"]]
    return [f"#depends-on:{d}" for d in it["deps"]] + [f"#used-by:{u}" for u in used_by]


def _sign() -> str:
    return "\n—Shibbieness\n—Claude\n"


# ---------------------------------------------------------------- build layer
def build_layer(root: Path, cap: Path) -> None:
    src = cap / "build" / "source"
    skip = {".git", "__pycache__", "dist", ".falsify_backup", "out", "refs", "capsules"}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if set(rel.parts) & skip or not p.is_file() or p.suffix == ".pyc":
            continue
        q = src / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, q)
    rename_nested_skills(src)
    ui = cap / "build" / "ui"
    for page in ("pixelgoblin.html", "pixelgoblin-pocket.html", "pixelgoblin-grounds.html", "src.html", "widget.src.html", "grounds.src.html"):
        _copy(root / "editor" / page, ui / page)
    for d in root.joinpath("docs").rglob("*.md"):
        _copy(d, cap / "build" / "specs" / d.relative_to(root / "docs"))
    _copy(root / "README.md", cap / "build" / "specs" / "README.md")
    cfg = cap / "build" / "config"
    for part in ("types", "flavors"):
        shutil.copytree(root / part, cfg / part, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("flavor.toml", "tests/FLOOR.json", "packaging/plugin/.claude-plugin/plugin.json", "packaging/plugin/.mcp.json"):
        _copy(root / f, cfg / Path(f).name)
    assets = cap / "build" / "assets"
    _copy(root / "docs" / "record" / "pixelgoblin-build-record.html", assets / "pixelgoblin-build-record.html")
    gal = assets / "gallery"
    gal.mkdir(parents=True, exist_ok=True)
    env = _clean_env(PYTHONHASHSEED="0")
    subprocess.run([sys.executable, str(root / "tools" / "record_gallery.py"), str(gal)], check=True, capture_output=True, env=env)
    subprocess.run([sys.executable, str(root / "tools" / "record_gallery.py"), str(gal), "--session4"], check=True, capture_output=True, env=env)
    for sub, why in (("ui", "the built pages and their sources"), ("specs", "the docs"), ("config", "type files, flavors, floor and plugin manifests"),
                     ("assets", "the build record and the gallery")):
        _write(cap / "build" / sub / "README.md", f"# build/{sub}/\n\nConvenience copies of {why}, for reading without digging into `build/source/`.\n"
               f"`build/source/` is canonical. The Forge validator checks these copies are byte-identical to it (the gallery is regenerated from seeds).\n" + _sign())


def rename_nested_skills(src: Path) -> None:
    """Rename the repository's inner SKILL.md files so the capsule holds exactly one."""
    for orig, new in RENAMED_SKILLS:
        a = src / orig
        if a.exists():
            a.rename(src / new)
    rows = "\n".join(f"| `{o}` | `{n}` |" for o, n in RENAMED_SKILLS)
    _write(src / "packaging" / "RENAMED_SKILLS.md",
           "# Renamed skill files\n\nA skill upload accepts exactly one `SKILL.md`: the capsule's router at the top. "
           "So inside `build/source/` the repository's own skill files carry their skill's name in front:\n\n"
           "| In the repository | In this capsule |\n|---|---|\n" + rows + "\n\n"
           "Nothing else changed: the contents are byte-identical. The Forge validator checks all four are here.\n\n"
           "## Before building from a copy\n\nCopy `build/source/` out, then in the copy run:\n\n"
           "```\npython3 tools/packaging_capsule.py restore .\n```\n\n"
           "That renames them back to `SKILL.md`. Then `python3 tools/package.py all` works as usual. "
           "The plugin build needs the `SKILL.md` names; without the restore it has no skills.\n" + _sign())


def restore_nested_skills(repo: Path) -> list[str]:
    """Undo rename_nested_skills in a copied-out build/source."""
    done = []
    for orig, new in RENAMED_SKILLS:
        a, b = repo / new, repo / orig
        if a.exists() and not b.exists():
            a.rename(b)
            done.append(orig)
    return done


def _copy(a: Path, b: Path) -> None:
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a, b)


# ---------------------------------------------------------------- codex
def mini_index(it: dict) -> str:
    rel = _rel(it)
    used_by = [o["id"] for o in ITEMS if it["id"] in o["deps"]]
    lines = [f"# {it['label']} — Mini-Index", "", f"## [codex/mini-indexes/{it['id']}.INDEX.md]", "", "---", "", "## What This Is", "", it["what"], "",
             "## Status", "", "| Field | Value |", "|---|---|", f"| Status | {it['ss'][1:].capitalize()} |", f"| Version | {CAPSULE_VERSION} (engine v0u1p0) |",
             f"| Last Updated | {FORGED} |", "| Owner | Shibbieness |", f"| Path | `{it['path']}` |", "",
             "## Tags", "", f"Structural: {it['st']}", f"Relational: {', '.join(rel) or 'none'}", f"Status: {it['ss']}", f"Narrative: {', '.join(it['nt'])}", "",
             "## Key Contents", "", "| Item | What It Is | Line / Section |", "|---|---|---|"]
    lines += [f"| {a} | {b} | `{c}` |" for a, b, c in it["keys"]]
    lines += ["", "## Dependencies", "", f"Depends on: {', '.join(it['deps']) or 'nothing inside the project'}",
              f"Required by: {', '.join(used_by) or 'nothing (leaf)'}", "External: Python 3.11+ standard library" + (", Node.js for parity checks" if it["id"] in ("transpiler-js", "gates") else ""), "",
              "## Navigation Notes", "", it["nav"], "", "## What This Is Not", "", it["not_"]]
    return "\n".join(lines) + "\n" + _sign()


CODEX_FILES = [  # capsule-level indexed items (no mini-index; they are the index layer itself)
    ("SKILL.md", "Router", "#index", "#complete", ["#session:5", "#access"]),
    ("PseudoSKILL.md", "Full operational reference", "#spec", "#complete", ["#session:5", "#naming"]),
    ("META.json", "Machine identity card", "#config", "#complete", ["#session:5"]),
    ("codex/MASTER_INDEX.md", "Master index", "#index", "#complete", ["#session:5"]),
    ("codex/NARRATIVE.md", "Project story", "#narrative", "#complete", ["#origin", "#pivot"]),
    ("codex/CHANGELOG.md", "Changelog", "#changelog", "#complete", ["#milestone"]),
    ("codex/TAG_REGISTRY.md", "Tag registry", "#registry", "#complete", ["#naming"]),
    ("codex/CALS_NAMESPACE.md", "CALS namespace", "#cals", "#complete", ["#session:5"]),
    ("codex/OPEN_QUESTIONS.md", "Open questions", "#open-questions", "#open", ["#session:5"]),
    ("dependencies/DEPENDENCY_MAP.md", "Dependency map", "#dependency-map", "#complete", ["#session:5"]),
    ("dependencies/dependency_graph.json", "Dependency graph", "#dependency-map", "#complete", ["#session:5"]),
    ("dependencies/external_deps.md", "External dependencies", "#dependency-map", "#complete", ["#session:5"]),
    ("dependencies/internal_deps.md", "Internal dependencies", "#dependency-map", "#complete", ["#session:5"]),
    ("pretune/README.md", "Pretune environment", "#test", "#complete", ["#session:5", "#validated"]),
    ("updates/UPDATE_INDEX.md", "Update index", "#index", "#complete", ["#session:5"]),
]


def master_index() -> str:
    L = [f"# MASTER INDEX — PixelGoblin PseudoSkill", "", f"Capsule {CAPSULE_VERSION} · engine v0u1p0 · forged {FORGED} · Compound Build", "",
         "Every indexed item in the capsule, with its tags. Modules and documents have a mini-index; the codex layer files are the index itself.", "",
         "## Modules and documents", "", "| Item | Path | Tags | Mini-index |", "|---|---|---|---|"]
    for it in ITEMS:
        L.append(f"| {it['label']} | `{it['path']}` | {' '.join(_tags(it))} | [`{it['id']}.INDEX.md`](mini-indexes/{it['id']}.INDEX.md) |")
    L += ["", "## Capsule layer", "", "| Item | Path | Tags |", "|---|---|---|"]
    for path, label, st, ss, nt in CODEX_FILES:
        L.append(f"| {label} | `{path}` | {' '.join([st, ss] + nt)} |")
    L += ["", "## Pretune scenarios", "", "| Scenario | What it draws |", "|---|---|"] + [f"| `pretune/scenarios/{sid}.json` | {d} |" for sid, d, _ in SCENARIOS]
    L += ["", "## Cross-reference: concept to item", "", "| Concept | Go to |", "|---|---|"]
    concept = [("same name, same goblin", "core-engine, rig, PseudoSKILL.md §2"),
               ("folk (races) and traits on any job", "resource-packs (races/, compendium/), typefile (compose), PseudoSKILL.md §6"),
               ("Book of Cities plants, animals, ores, biomes", "resource-packs, pack-builder"), ("ore weights from CRUCIBLE", "resource-packs (ores/), sandbox (grams)"),
               ("Aether Library avatars (supplement, never overwrite)", "resource-packs (aether/), cli (avatar)"),
               ("the sandbox / minigame", "sandbox, grounds-page, specs (play-goblin-grounds.md)"), ("VI Builder", "vi-builder, CALS_NAMESPACE.md"), ("tiers 8 to 256 px, eras", "rig, specs (tier-chain.md)"),
               ("side, back, isometric, top, free rotate", "rig3d, specs (views.md)"), ("clans / team colours", "typefile (with_team), type-files (clans.teams.toml)"),
               ("mounts and riders", "beast"), ("a city from names", "city, specs (build-a-city.md)"), ("zoom crowd to portrait", "rig (zoom_plan), outputs (zoom)"),
               ("expressions", "rig, outputs"), ("role signatures at 8 px", "rig (signature), gates (B20)"), ("items written as data", "typefile, rig, type-files (miner.toml)"),
               ("JavaScript parity", "transpiler-js, gates (B13)"), ("the widget", "pocket-widget"), ("the plugin and MCP tools", "plugin"), ("renamed <name>_SKILL.md files", "plugin, packaging (build/source/packaging/RENAMED_SKILLS.md)"),
               ("licences", "specs (stack.md, decisions ADR-010), PseudoSKILL.md §9"), ("what is next", "specs (gameplan.md), OPEN_QUESTIONS.md"),
               ("why a decision was made", "specs (decisions.md), NARRATIVE.md"), ("how things are checked", "gates, specs (gates.md)")]
    L += [f"| {a} | {b} |" for a, b in concept]
    return "\n".join(L) + "\n" + _sign()


def tag_registry() -> str:
    every = [(it["label"], _tags(it)) for it in ITEMS] + [(label, [st, ss] + nt) for _, label, st, ss, nt in CODEX_FILES]
    L = ["# TAG REGISTRY", "# PixelGoblin PseudoSkill", "", "This registry is the authoritative source for all tags used in this capsule.",
         "Before using a tag, verify it exists here. Before creating a new tag, add it here first.", "", "---", "",
         "## Structural Tags In Use", "", "| Tag | Applied To (in this project) | Count |", "|---|---|---|"]
    for t, d in STRUCTURAL.items():
        n = sum(1 for _, ts in every if t in ts)
        L.append(f"| {t} | {d} | {n or 'reserved'} |")
    L += ["", "## Relational Tags In Use", "", "| Tag | Relationship It Maps | Instances |", "|---|---|---|"]
    rels: dict[str, list[str]] = {}
    for it in ITEMS:
        for r in _rel(it):
            rels.setdefault(r, []).append(it["id"])
    for r in sorted(rels):
        L.append(f"| {r} | carried by {', '.join(rels[r])} | {len(rels[r])} |")
    L += ["", "## Status Tags In Use", "", "| Tag | Items Currently Carrying This Status |", "|---|---|"]
    for t, d in STATUS.items():
        who = [lab for lab, ts in every if t in ts]
        L.append(f"| {t} | {', '.join(who) or '(none at forge)'} |")
    L += ["", "## Narrative Tags In Use", "", "| Tag | Items Tagged With This | Phase It Represents |", "|---|---|---|"]
    for t, (phase, ex) in NARRATIVE.items():
        who = [lab for lab, ts in every if t in ts]
        L.append(f"| {t} | {', '.join(who) or '(none at forge)'} | {phase}: {ex} |")
    L += ["", "## Project-Specific Tags", "", "Tags unique to this project, not in the standard schema. Scoped to this capsule only.", "",
          "| Tag | Type | Meaning | First Used |", "|---|---|---|---|"]
    L += [f"| {t} | narrative | {m} | {FORGED} |" for t, m in PROJECT_TAGS.items()]
    L += ["", "## Tag rules (from the output spec)", "", "- Exactly one structural tag and one status tag per indexed item; at least one narrative tag.",
          "- Lowercase, hyphens, no spaces; `#type:value` for relational tags.", "- Registered here before use. The Forge validator refuses any tag not listed.", "",
          "---", "", "Registry version: 1.0", f"Last updated: {FORGED}"]
    return "\n".join(L) + "\n" + _sign()


def changelog() -> str:
    L = ["# CHANGELOG — PixelGoblin PseudoSkill", "", f"Versions use Mark's VUP format (vMAJORuMINORpPATCH). {CAPSULE_VERSION} is the spec's 1.0.0.", "",
         f"## {CAPSULE_VERSION} — {FORGED} — FORGE", "", "**Summary:** The initial capsule: PixelGoblin engine v0u1p0 after five sessions, indexed and packaged.",
         "", "**Source:** Compound Build (File Build pass over the repository, then Conversation Build pass over sessions 1 to 5)", "",
         f"**Session:** {SESSION}", "", "**Tags:** #milestone #session:5 #access", "", "### Added", ""]
    L += [f"- {it['label']} (`{it['path']}`): {it['what'].split('. ')[0].rstrip('.')}. {it['st']} {it['ss']}" for it in ITEMS]
    L += [f"- {label} (`{path}`) {st} {ss}" for path, label, st, ss, _ in CODEX_FILES]
    L += [f"- Pretune scenario `{sid}`: {d}. #test #complete" for sid, d, _ in SCENARIOS]
    L += ["", "### Changed", "", "- Nothing: first entry.", "", "### Deprecated", "", "- Nothing.", "", "### Removed", "", "- Nothing.", "", "### Fixed", "",
          "- Nothing at forge. Bugs fixed during the sessions are in codex/NARRATIVE.md and the build record.", "", "### Notes", "",
          "- Density: the source sessions were short but dense (five sessions, each setting several architectural decisions at once). The dense-session protocol was applied: three passes (architecture, decisions, vocabulary and narrative).",
          "- Mode: Compound. The repository is canonical for current state; the conversations are canonical for reasoning.",
          f"- Naming: the capsule is `{NAME}`, following Mark's current capsule names (helix-pseudoskill, lexis-pseudoskill) rather than the spec's `-codex` suffix. See OPEN_QUESTIONS Q9.",
          "- Validation: every check in the Forge validation checklist passed before packaging (tools/packaging_capsule.py validate()). Gate B21 runs the same checks.",
          "- Mark's reference images are not in this capsule and never will be.", "",
          f"## {PATCH_VERSION} — 2026-09-27 — CORRECTION", "", "**Summary:** Upload compatibility. A skill upload accepts one SKILL.md and only the header fields name, description, license, allowed-tools, metadata and compatibility.",
          "", "**Tags:** #access #session:5", "", "### Changed", "",
          "- The four inner skill files in `build/source/` are renamed `<name>_SKILL.md` (list and restore steps: `build/source/packaging/RENAMED_SKILLS.md`). Contents unchanged.",
          "- SKILL.md header: version, author, forged and the other extra fields moved under `metadata:`. Values unchanged. META.json holds them too.",
          "- The validator checks there is exactly one SKILL.md and that the renamed files are present. `tools/packaging_capsule.py restore <dir>` undoes the rename in a copy.",
          "", "### Notes", "", "- The repository keeps its SKILL.md names, so the plugin builds exactly as before. Nothing else in the capsule changed."]
    return "\n".join(L) + "\n" + _sign()


def dependency_graph() -> dict:
    nodes = [{"id": it["id"], "label": it["label"], "type": it["st"][1:], "status": it["ss"][1:], "path": it["path"], "tags": _tags(it)} for it in ITEMS]
    notes = {("cli", "rig3d"): "view, turnaround and ride commands", ("transpiler-js", "rig"): "rig.py is transpiled to pg-rig.gen.js",
             ("plugin", "cli"): "the MCP server runs cli.main in-process", ("gates", "plugin"): "B21 builds the plugin and talks to its server",
             ("beast", "rig3d"): "mounts share the voxel renderer", ("city", "scene-warren"): "the village holds the citizens"}
    edges = [{"from": it["id"], "to": d, "type": "depends-on", "notes": notes.get((it["id"], d), "")} for it in ITEMS for d in it["deps"]]
    return {"project": "pixelgoblin", "version": CAPSULE_VERSION, "nodes": nodes, "edges": edges}


def _cycles(g: dict) -> list[list[str]]:
    adj: dict[str, list[str]] = {}
    for e in g["edges"]:
        adj.setdefault(e["from"], []).append(e["to"])
    out, state = [], {}

    def dfs(n, stack):
        state[n] = 1
        for m in adj.get(n, []):
            if state.get(m) == 1:
                out.append(stack[stack.index(m):] + [m])
            elif not state.get(m):
                dfs(m, stack + [m])
        state[n] = 2
    for n in adj:
        if not state.get(n):
            dfs(n, [n])
    return out


def dependency_map(g: dict) -> str:
    L = ["# DEPENDENCY MAP — PixelGoblin", "", "## Entry Points", "",
         "- `python3 -m pixelgoblin` (build/source/pixelgoblin/cli.py): the command line, 28 commands.",
         "- `build/ui/pixelgoblin.html` and `build/ui/pixelgoblin-pocket.html`: the browser pages.",
         "- `build/source/packaging/plugin/server/pixelgoblin_mcp.py`: the MCP server inside the plugin.",
         "- `build/source/tests/gate.py`: the gates.", "", "## Module Dependency Tree", ""]
    for it in ITEMS:
        used_by = [o["id"] for o in ITEMS if it["id"] in o["deps"]]
        L += [it["id"], f"└─ depends on: {', '.join(it['deps']) or 'nothing inside the project'}",
              f"└─ required by: {', '.join(used_by) or 'nothing (leaf node)'}", f"└─ status: {it['ss']}", ""]
    L += ["## External Dependencies", "", "| Dependency | Version | Used By | Required? |", "|---|---|---|---|",
          "| Python standard library | 3.11 or newer (tomllib) | every module | yes |", "| Node.js | 18 or newer | gates (B13 parity) | only for the gates |",
          "| A browser | any current | workbench, pocket widget | only for the pages |", "| Google Fonts | - | the pages' typefaces | no (fallback fonts) |", "",
          "Details: `external_deps.md`. Module-level imports: `internal_deps.md`.", "", "## Dependency Health", ""]
    cyc = _cycles(g)
    L += [f"Circular dependencies: {'none' if not cyc else '; '.join(' → '.join(c) for c in cyc)}", "Unresolved dependencies: none",
          "Deprecated dependencies: none (ADR-006, the egui editor, was superseded before it was built)"]
    return "\n".join(L) + "\n" + _sign()


def internal_deps(root: Path) -> str:
    rows = []
    for p in sorted((root / "pixelgoblin").rglob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.level:
                base = n.module or ""
                if base:
                    mods.add(base)
                else:
                    mods.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom) and (n.module or "").startswith("pixelgoblin"):
                mods.add(n.module.replace("pixelgoblin.", ""))
        rows.append((p.relative_to(root).as_posix(), sorted(mods)))
    L = ["# Internal dependencies", "", "Generated from the import statements of `build/source/pixelgoblin/` (relative imports shown by module name).", "",
         "| Module | Imports from the package |", "|---|---|"] + [f"| `{m}` | {', '.join(f'`{x}`' for x in d) or '-'} |" for m, d in rows]
    L += ["", "Cross-language: `editor/pg-rig.gen.js` is generated from `gen/rig.py`, `gen/rig3d.py` and `gen/beast.py` by `tools/transpile_rig.py`.",
          "`tools/build_editor.py` embeds `pg-core.js` + `pg-rig.js` (with the generated geometry) and every type file into both pages."]
    return "\n".join(L) + "\n" + _sign()


def update_structure(cap: Path) -> None:
    slots = {
        "companions": ("Extended context documents that expand on existing project material: why decisions were made, deeper narrative, extended specifications. They do not replace or modify core documents.",
                       ["An explainer of the depth rules for one feature", "A deeper write-up of one ADR"], ["Plans for new work — gameplans/", "Corrections to the core — the Update Skill"], "#companion"),
        "gameplans": ("Implementation plans, phased build sequences and roadmaps for work to be done, referencing the core build as context.",
                      ["Pose as data", "Per-feature depth overrides", "Isometric scenes", "8-direction animation atlas", "City life"], ["Finished how-tos — build-guides/"], "#gameplan"),
        "build-guides": ("Step-by-step instructions for building, setting up, deploying or running something within PixelGoblin.",
                         ["Installing the plugin", "Re-blessing goldens with a witness", "Publishing the widget"], ["Reference tables — documentation/"], "#build-guide"),
        "documentation": ("Technical documentation that supplements the core specs: API references, usage guides, integration and format specifications.",
                          ["MCP tool reference", "Type-file additions for new generators"], ["Narrative — companions/"], "#api-ref"),
        "tests": ("Test suites, validation scripts, expected-output definitions and testing documentation, including pretune scenarios promoted to formal tests.",
                  ["New pretune scenarios with expected hashes", "Extra falsify mutations (as proposals)"], ["Changes to tests/gate.py itself — the Update Skill"], "#test"),
        "index-updates": ("Revised or extended versions of MASTER_INDEX.md when scope has grown enough that the original is incomplete. Addenda, never replacements.",
                          ["An addendum listing modules added after v0u1p0"], ["Mini-indexes for new artifacts — they sit beside the artifact in its slot"], "#index"),
        "changelog-updates": ("Changelog entries from Companion Builder sessions, in the changelog notation standard, later folded into CHANGELOG.md by the Update Skill.",
                              ["COMPANION entries, one per session"], ["Edits to codex/CHANGELOG.md — the Update Skill"], "#changelog"),
        "misc": ("Legitimate additions that fit no named slot. Each must say what it is, why it fits nowhere else, and a proposed slot name if the type recurs.",
                 ["pending-core-updates-YYYYMMDD.md from the Hard Boundary Protocol"], ["Anything that fits a named slot"], "#misc"),
    }
    up = cap / "updates"
    idx = [f"# UPDATE INDEX — PixelGoblin", "", "## Post-Build Additions Register", "",
           "> This index is the authoritative record of everything added to this capsule", "> after the initial build. It is maintained by the Companion Builder mode.",
           "> For core build contents, see codex/MASTER_INDEX.md.", "", "Companion Builder sessions: 0", "", f"Last updated: {FORGED}", "", "---", "", "## Contents by Slot", ""]
    for slot, (purpose, yes, no, stag) in slots.items():
        idx.append(f"### {slot}/ [empty at forge]")
        idx.append("")
        init = [f"# {slot.upper()} — Slot Initialization", "", f"## updates/{slot}/INIT.md", "",
                "> This slot was initialized at capsule forge. It is empty until a Companion", "> Builder session adds content here.", "",
                "## Purpose", "", purpose, "", "## What Belongs Here", ""] + [f"- {y}" for y in yes] + ["", "## What Does Not Belong Here", ""] + [f"- {n}" for n in no]
        init += ["", "## Naming Convention", "", "Lowercase words with hyphens, then the date.", "", f"Example: pose-as-data-{FORGED.replace('-', '')}.md", "",
                 "## Required Tags for Items in This Slot", "", f"Structural: {stag}", "Status: any valid status tag", "Narrative: at minimum #session:[N]", "",
                 "## Index Requirement", "", "Every file added here must have a mini-index entry in:", "", f"updates/{slot}/[filename].INDEX.md", "",
                 "And must be logged in: updates/UPDATE_INDEX.md"]
        _write(up / slot / "INIT.md", "\n".join(init) + "\n" + _sign())
        _write(up / slot / "EMPTY.md", f"# updates/{slot}/ — EMPTY\n\nEmpty at forge ({FORGED}): no Companion Builder session has run yet.\n\n"
               f"What would populate it: {yes[0].lower()}, or any other item described in INIT.md.\n" + _sign())
    idx += ["---", "", f"No post-build additions yet. Forge date: {FORGED}"]
    _write(up / "UPDATE_INDEX.md", "\n".join(idx) + "\n" + _sign())


# What a process needs from its OS just to start (Windows only; none exist
# elsewhere). The gate keeps the same set: see OS_PLUMBING in tests/gate.py.
_OS_PLUMBING = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT")


def _clean_env(**extra: str) -> dict:
    env = {k: os.environ[k] for k in _OS_PLUMBING if k in os.environ}
    env["PATH"] = "/usr/bin:/bin" if os.name != "nt" else os.environ.get("PATH", "")
    env.update(extra)
    return env


def pretune(root: Path, cap: Path) -> None:
    pt = cap / "pretune"
    env = _clean_env(PYTHONHASHSEED="0", HOME=str(cap))
    results = []
    for sid, desc, argv in SCENARIOS:
        out = pt / "expected_outputs" / (sid if argv[0] in ("city", "sandbox") else f"{sid}.png")
        full = ["python3", "-m", "pixelgoblin"] + argv + ["--out", str(out)]
        if argv[0] not in ("city", "sandbox"):
            full += ["--scale", "1"]
        out.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable] + full[1:], cwd=root, capture_output=True, text=True, env=env, encoding="utf-8")
        files = sorted(out.rglob("*.png")) if out.is_dir() else [out]
        hashes = {f.relative_to(pt / "expected_outputs").as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.exists()}
        _write(pt / "scenarios" / f"{sid}.json", json.dumps({"id": sid, "asks": desc, "command": ["python3", "-m", "pixelgoblin"] + argv + ["--out", out.relative_to(pt / "expected_outputs").as_posix()] + (["--scale", "1"] if argv[0] not in ("city", "sandbox") else []),
                                                             "run_from": "build/source", "expected_sha256": hashes}, indent=1))
        said = (r.stdout.strip().splitlines()[-1:] or [r.stderr.strip()[-200:]])[0].replace(str(pt / "expected_outputs") + "/", "")
        results.append((sid, r.returncode == 0 and bool(hashes), [said]))
    L = [f"# Pretune results — forge run {FORGED}", "", "Each scenario was run from `build/source/` and its output hashed into `scenarios/<id>.json`.", "",
         "| Scenario | Result | Engine said |", "|---|---|---|"] + [f"| `{s}` | {'PASS' if ok else 'FAIL'} | {msg[0][:120] if msg else ''} |" for s, ok, msg in results]
    _write(pt / "results" / f"forge-{FORGED.replace('-', '')}.md", "\n".join(L) + "\n" + _sign())
    if not all(ok for _, ok, _ in results):
        raise SystemExit("a pretune scenario failed at forge")


# ---------------------------------------------------------------- forge
def build_capsule(root: Path, dist: Path) -> Path:
    cap = dist / NAME
    if cap.exists():
        shutil.rmtree(cap)
    hand = root / "packaging" / "capsule"
    shutil.copytree(hand, cap, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    build_layer(root, cap)
    update_structure(cap)
    for it in ITEMS:
        _write(cap / "codex" / "mini-indexes" / f"{it['id']}.INDEX.md", mini_index(it))
    _write(cap / "codex" / "MASTER_INDEX.md", master_index())
    _write(cap / "codex" / "TAG_REGISTRY.md", tag_registry())
    _write(cap / "codex" / "CHANGELOG.md", changelog())
    g = dependency_graph()
    _write(cap / "dependencies" / "dependency_graph.json", json.dumps(g, indent=1, ensure_ascii=False))
    _write(cap / "dependencies" / "DEPENDENCY_MAP.md", dependency_map(g))
    _write(cap / "dependencies" / "internal_deps.md", internal_deps(root))
    pretune(root, cap)
    meta = {"project_name": "PixelGoblin", "codex_name": NAME, "codex_version": "1.0.0", "version": PATCH_VERSION, "version_format": "VUP",
            "engine_version": "v0u1p0", "forged_date": FORGED, "author": "Shibbieness", "co_author": "Claude", "organization": "M MAOU LLC",
            "compiler_mode": "conversation+file", "build_mode": "compound", "cals_namespace": True, "build_layer_present": True, "pretune_layer_present": True,
            "immutable_core": True, "update_structure_version": "1.0", "tags": ["#determinism", "#tier-chain", "#views", "#city", "#parity", "#access", "#packs", "#grounds", "#milestone"],
            "composes_with": ["spire", "slm-e", "book-of-cities", "book-of-cities-compendium-builder", "aether-library-pseudoskill", "crucible", "vi-builder",
                              "gilwright", "dropzone", "cals", "working-with-mark", "pseudoskills-builder", "eexpand"],
            "companion_plugin": "pixelgoblin (dist/pixelgoblin.plugin)", "companion_builder_sessions": 0, "last_update": None}
    _write(cap / "META.json", json.dumps(meta, indent=1, ensure_ascii=False))
    problems = validate(cap)
    if problems:
        raise SystemExit("capsule failed validation:\n  " + "\n  ".join(problems))
    return cap


# ---------------------------------------------------------------- validation (the Forge checklist, as code)
SKILL_SECTIONS = ["IMMUTABILITY NOTICE", "## Project Identity", "## What This Project Is", "## Navigation Map", "## Current State", "## Key Vocabulary", "## CALS Namespace", "## Post-Build Additions"]


def validate(cap: Path) -> list[str]:
    P: list[str] = []
    need = ["SKILL.md", "codex", "dependencies", "build", "pretune", "updates", "META.json"]
    P += [f"missing top-level entry {n}" for n in need if not (cap / n).exists()]
    P += [f"missing codex file {n}" for n in ("MASTER_INDEX.md", "NARRATIVE.md", "CHANGELOG.md", "TAG_REGISTRY.md", "OPEN_QUESTIONS.md") if not (cap / "codex" / n).exists()]
    if not (cap / "codex" / "CALS_NAMESPACE.md").exists() and not (cap / "codex" / "CALS_NAMESPACE_ABSENT.md").exists():
        P.append("codex needs CALS_NAMESPACE.md or CALS_NAMESPACE_ABSENT.md")
    P += [f"missing dependency file {n}" for n in ("DEPENDENCY_MAP.md", "dependency_graph.json", "external_deps.md", "internal_deps.md") if not (cap / "dependencies" / n).exists()]
    for sub in ("source", "ui", "specs", "config", "assets"):
        d = cap / "build" / sub
        if not d.is_dir() or not any(d.iterdir()):
            P.append(f"build/{sub}/ is missing or empty (use EMPTY.md)")
    for sub in ("scenarios", "expected_outputs", "results"):
        d = cap / "pretune" / sub
        if not d.is_dir() or not any(d.iterdir()):
            P.append(f"pretune/{sub}/ is missing or empty (use EMPTY.md)")
    if not (cap / "pretune" / "README.md").exists():
        P.append("pretune/README.md missing")
    slots = ["companions", "gameplans", "build-guides", "documentation", "tests", "index-updates", "changelog-updates", "misc"]
    for s in slots:
        init = cap / "updates" / s / "INIT.md"
        if not init.exists():
            P.append(f"updates/{s}/INIT.md missing")
            continue
        t = init.read_text(encoding="utf-8")
        P += [f"updates/{s}/INIT.md lacks '{h}'" for h in ("## Purpose", "## What Belongs Here", "## What Does Not Belong Here", "## Naming Convention") if h not in t]
        if len([p for p in (cap / "updates" / s).iterdir()]) == 1:
            P.append(f"updates/{s}/ has INIT.md but no EMPTY.md or content")
    if not (cap / "updates" / "UPDATE_INDEX.md").exists():
        P.append("updates/UPDATE_INDEX.md missing")
    for e in cap.rglob("EMPTY.md"):
        if "What would populate it" not in e.read_text(encoding="utf-8") and "would populate" not in e.read_text(encoding="utf-8"):
            P.append(f"{e.relative_to(cap)} does not say what would populate it")
    try:
        meta = json.loads((cap / "META.json").read_text(encoding="utf-8"))
        for k in ("project_name", "codex_version", "forged_date", "author", "organization", "compiler_mode", "cals_namespace", "build_layer_present",
                  "pretune_layer_present", "immutable_core", "update_structure_version", "tags", "companion_builder_sessions"):
            if k not in meta:
                P.append(f"META.json lacks {k}")
    except (OSError, json.JSONDecodeError) as e:
        P.append(f"META.json does not parse: {e}")
    # SKILL.md
    sk = (cap / "SKILL.md").read_text(encoding="utf-8") if (cap / "SKILL.md").exists() else ""
    m = re.match(r"---\n(.*?)\n---\n", sk, re.S)
    if not m:
        P.append("SKILL.md has no frontmatter")
    else:
        fm = m.group(1)
        top = set(re.findall(r"^([A-Za-z_-]+):", fm, re.M))
        extra = top - {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
        if extra:
            P.append(f"SKILL.md frontmatter has keys a skill upload rejects (move them under metadata:): {sorted(extra)}")
        for k in ("name:", "description:", "metadata:"):
            if not re.search(rf"^{k}", fm, re.M):
                P.append(f"SKILL.md frontmatter lacks {k}")
        for k in ("version:", "author:", "forged:", "immutable_core:", "update_structure_version:"):
            if not re.search(rf"^  {k}", fm, re.M):
                P.append(f"SKILL.md frontmatter metadata lacks {k}")
        desc_txt = re.search(r'^description: "(.*)"$', fm, re.M)
        if desc_txt and (len(desc_txt.group(1)) > 1024 or "<" in desc_txt.group(1) or ">" in desc_txt.group(1)):
            P.append("SKILL.md description must be at most 1024 characters with no angle brackets")
        if not re.search(rf"^name: {NAME}$", fm, re.M):
            P.append(f"SKILL.md name must be {NAME}")
        desc = re.search(r'^description: "(.*)"$', fm, re.M)
        if not desc or len(re.findall(r"[.!?](?:\s|$)", desc.group(1))) < 3:
            P.append("SKILL.md description must follow the three-sentence pattern")
        body = sk[m.end():]
        if not body.lstrip().startswith("> ⚠️ IMMUTABILITY NOTICE"):
            P.append("the Immutability Notice must come immediately after the frontmatter")
        pos = [body.find(s) for s in SKILL_SECTIONS]
        if -1 in pos:
            P.append(f"SKILL.md lacks sections: {[s for s, p in zip(SKILL_SECTIONS, pos) if p == -1]}")
        elif pos != sorted(pos):
            P.append("SKILL.md sections are out of order")
        for f in ("codex/MASTER_INDEX.md", "codex/NARRATIVE.md", "codex/CALS_NAMESPACE.md", "codex/CHANGELOG.md", "codex/OPEN_QUESTIONS.md", "codex/TAG_REGISTRY.md",
                  "dependencies/DEPENDENCY_MAP.md", "updates/UPDATE_INDEX.md", "PseudoSKILL.md", "build/source/", "build/ui/", "build/specs/", "build/config/", "build/assets/", "pretune/"):
            if f"`{f}" not in body:
                P.append(f"SKILL.md Navigation Map does not reference {f}")
        if len(body.split()) > 5000:
            P.append("SKILL.md is too long for a router (over 5000 words)")
    # exactly one SKILL.md (a skill upload rejects more); the renamed ones are present
    skills = [q.relative_to(cap).as_posix() for q in cap.rglob("SKILL.md")]
    if skills != ["SKILL.md"]:
        P.append(f"the capsule must hold exactly one SKILL.md, at the top; found {sorted(skills)}")
    for _, new in RENAMED_SKILLS:
        if not (cap / "build" / "source" / new).exists():
            P.append(f"renamed skill file build/source/{new} is missing")
    if not (cap / "build" / "source" / "packaging" / "RENAMED_SKILLS.md").exists():
        P.append("build/source/packaging/RENAMED_SKILLS.md is missing")
    # index completeness
    mi = (cap / "codex" / "MASTER_INDEX.md").read_text(encoding="utf-8") if (cap / "codex" / "MASTER_INDEX.md").exists() else ""
    for it in ITEMS:
        f = cap / "codex" / "mini-indexes" / f"{it['id']}.INDEX.md"
        if not f.exists():
            P.append(f"no mini-index for {it['id']}")
            continue
        t = f.read_text(encoding="utf-8")
        P += [f"{f.name} lacks '{h}'" for h in ("## What This Is", "## Status", "## Tags", "## Key Contents", "## Dependencies", "## Navigation Notes", "## What This Is Not") if h not in t]
        if f"{it['id']}.INDEX.md" not in mi:
            P.append(f"MASTER_INDEX does not reference {it['id']}")
        if not (cap / it["path"]).exists():
            P.append(f"{it['id']} points at {it['path']}, which is not in the capsule")
    for path, *_ in CODEX_FILES:
        if f"`{path}`" not in mi:
            P.append(f"MASTER_INDEX does not list {path}")
        if not (cap / path).exists():
            P.append(f"indexed file {path} does not exist")
    # tags
    reg = (cap / "codex" / "TAG_REGISTRY.md").read_text(encoding="utf-8") if (cap / "codex" / "TAG_REGISTRY.md").exists() else ""
    registered = set(re.findall(r"\| (#[a-z0-9:,.-]+) \|", reg))
    every = [(it["id"], _tags(it) + _rel(it)) for it in ITEMS] + [(p, [st, ss] + nt) for p, _, st, ss, nt in CODEX_FILES]
    for who, ts in every:
        if sum(t in STRUCTURAL for t in ts) != 1:
            P.append(f"{who} needs exactly one structural tag")
        if sum(t in STATUS for t in ts) != 1:
            P.append(f"{who} needs exactly one status tag")
        if not any(t in NARRATIVE or t in PROJECT_TAGS for t in ts):
            P.append(f"{who} needs at least one narrative tag")
        for t in ts:
            if t not in registered:
                P.append(f"tag {t} on {who} is not in TAG_REGISTRY.md")
    for f in cap.joinpath("codex").rglob("*.md"):
        for t in set(re.findall(r"(?<![\w/`&])#[a-z][a-z0-9-]*(?::[a-z0-9.-]+(?:,[a-z0-9.-]+)*)?", f.read_text(encoding="utf-8"))):
            if t not in registered and t not in ("#not",):
                P.append(f"phantom tag {t} in {f.relative_to(cap)}")
    # dependencies
    try:
        g = json.loads((cap / "dependencies" / "dependency_graph.json").read_text(encoding="utf-8"))
        ids = {n["id"] for n in g["nodes"]}
        for n in g["nodes"]:
            if not (cap / n["path"]).exists():
                P.append(f"graph node {n['id']} path {n['path']} is not a real file")
            for k in ("id", "label", "type", "status", "path", "tags"):
                if k not in n:
                    P.append(f"graph node lacks {k}")
        for e in g["edges"]:
            if e["from"] not in ids or e["to"] not in ids:
                P.append(f"graph edge {e} names an unknown node")
        dm = (cap / "dependencies" / "DEPENDENCY_MAP.md").read_text(encoding="utf-8")
        for i in ids:
            if f"\n{i}\n└─ depends on" not in dm:
                P.append(f"DEPENDENCY_MAP.md lacks {i}")
        cyc = _cycles(g)
        if cyc and "Circular dependencies: none" in dm:
            P.append("a cycle exists but DEPENDENCY_MAP.md says none")
    except (OSError, json.JSONDecodeError, KeyError) as e:
        P.append(f"dependency_graph.json does not parse: {e}")
    # changelog
    cl = (cap / "codex" / "CHANGELOG.md").read_text(encoding="utf-8") if (cap / "codex" / "CHANGELOG.md").exists() else ""
    first = re.search(r"^## (\S+) — (\S+) — (\w+)", cl, re.M)
    if not first or first.group(3) != "FORGE" or first.group(1) not in ("1.0.0", "v1u0p0"):
        P.append("the first CHANGELOG entry must be FORGE at 1.0.0 (v1u0p0)")
    for it in ITEMS:
        if f"{it['label']} (`{it['path']}`)" not in cl:
            P.append(f"CHANGELOG Added lacks {it['id']}")
    # copies agree with source; nothing private
    src = cap / "build" / "source"
    for a, b in (("build/ui/pixelgoblin.html", "editor/pixelgoblin.html"), ("build/ui/pixelgoblin-pocket.html", "editor/pixelgoblin-pocket.html"),
                 ("build/specs/explanation/decisions.md", "docs/explanation/decisions.md"), ("build/config/FLOOR.json", "tests/FLOOR.json")):
        if (cap / a).exists() and (src / b).exists() and (cap / a).read_bytes() != (src / b).read_bytes():
            P.append(f"{a} differs from build/source/{b}")
    for p in cap.rglob("*"):
        if "refs" in p.relative_to(cap).parts or p.name.endswith(".pyc") or "__pycache__" in p.parts:
            P.append(f"must not be packaged: {p.relative_to(cap)}")
    for s in (cap / "pretune" / "scenarios").glob("*.json"):
        for rel, h in json.loads(s.read_text(encoding="utf-8"))["expected_sha256"].items():
            f = cap / "pretune" / "expected_outputs" / rel
            if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
                P.append(f"pretune expected output {rel} does not match its hash")
    return P


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):  # a pipe on Windows defaults to cp1252; write UTF-8 everywhere
        _s.reconfigure(encoding="utf-8")
    here = Path(__file__).resolve().parent.parent
    if len(sys.argv) > 2 and sys.argv[1] == "validate":
        probs = validate(Path(sys.argv[2]))
        print("\n".join(probs) or "capsule valid")
        sys.exit(1 if probs else 0)
    if len(sys.argv) > 2 and sys.argv[1] == "restore":
        back = restore_nested_skills(Path(sys.argv[2]))
        print("\n".join(f"restored {b}" for b in back) or "nothing to restore")
        sys.exit(0)
    print(build_capsule(here, here / "dist"))
