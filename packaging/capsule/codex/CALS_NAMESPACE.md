# CALS Namespace — PixelGoblin

Tags: #cals #complete #session:5

## Conceptual AI Logic Layer

> This namespace is closed. It describes PixelGoblin's conceptual AI logic
> in PixelGoblin's terms. It does not extend or reference CALS namespaces
> from other projects. See the global CALS skill for the general framework.

---

## What This Namespace Governs

PixelGoblin has no model inside it (ADR-003), so its CALS logic is about routing between deterministic components with different characters, and about the one designed-but-unbuilt place where a model could enter. It governs: which component answers a request (generate, convert, learn, draw a view, build a city); which surface to hand Mark (widget, workbench, plugin tools, command line); what must be checked before a result is trusted (gates, verdicts, hazards); and the rule that anything a future model slot produces is re-quantised by the core before it counts.

## System Components (CALS Characterization)

| Component | Type | Cognitive Character | Optimal Task Surface |
|---|---|---|---|
| Generators (mask, L-system, parallax, tiles, uikit) | module | Pure synthesis from a type file and a seed | Variety at scale: sheets of creatures, tiles, backdrops, UI |
| Rig | module | Identity-preserving synthesis across sizes | One character at every tier and era |
| Lift (rig3d) and beast | module | Inference of depth from a front drawing | Views, turnarounds, riders |
| City | module | Population synthesis keyed by names | Towns, households, crowds |
| Convert and likeness | module | Reduction and learning from an example | Turning images into pixel art; new type files from one image |
| Verdicts and hazards | module | Assessment, never production | Is it to spec? Does it fit a target? Is it safe to ship? |
| Gates and falsify | test | Verification of the whole | Before any claim or release |
| Widget, workbench | ui | Direct manipulation | Looking, turning, choosing, saving |
| Plugin tools and skills | module | Conversational access | Making art from a sentence |
| Optional model slot | planned | Open-ended concept exploration | Only if Mark wants it (P8), never in the core |

## Routing Map

| Task Category | Routed To | Rationale |
|---|---|---|
| "A goblin called X" | Rig (+ lift for any non-front view) | The name is the seed; the rig owns identity |
| "From the side / top / any angle" | Lift (rig3d) | Views are projections of one model; never draw a view by hand |
| "On a boar / warg" | Beast | Mounts share the renderer and scale |
| "In clan colours" | typefile.with_team, then Rig | Clans are data; the type hash is kept |
| "A town from these names" | City | Each person from their own name |
| "Make this picture pixel art" | Convert | Tag profiles bound colours and cleanup |
| "More things like this example" | Likeness | Learns a type file, then Generators take over |
| "Is it right / safe?" | Verdicts, hazards | Two verdicts, never merged |
| "Just let me play with it" | Widget (Pocket) or Workbench | Direct manipulation beats description |
| "Make a dwarf / elf / orc ..." | Folk overlay (resource-packs) on a job, via compose | Folk are bodies, jobs are roles; never a new role per folk |
| "Show me the Book of Cities' ores / plants / animals" | Resource packs (pack sheets) | Generated from the source catalogs; colours flagged when inferred |
| "Draw this Aether soul" | avatar (souls.toml) | Seeded by soul name; a supplement, never an overwrite |
| "A sandbox / minigame / world for my game" | Goblin Grounds (page) or sandbox export | The engine plans; the page plays; world.json carries CRUCIBLE weights |
| "Change how the engine works" | Engine skill, then gates | Every change passes B00–B21 and falsify |
| "Explore a loose concept" | Optional model slot (designed), output re-quantised | Strict palette or commercial work stays core-only |

## Like-But-Different Relationships

- **Rig vs Lift.** Both draw the same goblin. The rig is authored (the front drawing, the tier chain); the lift is inferred from it. Route art-direction questions to the rig's data, never to the lift's depth rules alone.
- **Workbench vs Pocket.** Same engine, same pixels. The workbench is for building and checking; the Pocket is for quick making and sharing. Route by how much Mark wants to touch.
- **Spec verdict vs target verdict.** Both judge a sprite. One asks "does it match its type file?", the other "does it fit this platform?". Never merge them (ADR-013).

## Same-But-Different Relationships

- **Python engine vs JavaScript engine.** The same component in two contexts. Python is the source of truth; JavaScript is transpiled or parity-gated. Route every geometry change to Python first.
- **Plugin skill vs this capsule.** Both carry PixelGoblin knowledge. The plugin skill is for doing (make art now); the capsule is for knowing (why, what depends on what, what is open). Route by whether the task produces pixels or decisions.
- **Name seed vs number seed.** Both select a character. Names are for people and cities; numbers are for sheets and variety sweeps.

## Constrained Logic Structures

- **Integer-only runtime.** If a float enters, parity and cross-platform determinism fail silently. Guarded by B02 and B13.
- **Named streams.** If two parts share a stream, adding one changes the other (the ADR-008 failure). Guarded by B01 and a mutation.
- **Genome blind to tier.** If the genome reads the tier, sizes drift into different characters. Guarded by B16's coherence floors.
- **One model for all views.** If any view is drawn separately, views can disagree. Guarded by B18.
- **Model slot outside the core.** If a model's output were used unquantised, palettes and determinism would break. Designed rule: always re-quantise; strict and commercial work routes core-only.
- **Scrub.** If stack terms enter vanilla code, the vanilla pack cannot ship on its own. Guarded by B12.

## VI Builder Registration Profile

The one permitted cross-namespace reference (following LEXIS). Full text: `build/source/packaging/vi-builder/REGISTRATION.md`.

```
Process ID:        pixelgoblin-pixel-art-v1
Filesystem source: pixelgoblin-pseudoskill/ (this capsule) or pixelgoblin/ (the repo)
Tier:              4 — Inference (4a Prompt Capsule; 4b RAG Package over type files and packs)
Staleness:         MEDIUM — packs and palettes change with the game; the engine contract does not
Routing signal:    pixel art, sprite, goblin, folk, tier chain, view, mount, clan, city, resource pack, ore weight, sandbox
Castle:            Pixel Art Castle (proposed)
Phase relevance:   Phase 1 (Tier 4 Prompt Capsule ingest)

Process ID:        pixelgoblin-engine-v0u1p0
Tier:              2 — Application (2b Start/Stop Job: the command line; 2a System Daemon: the MCP server)
Endpoints:         query = pixelgoblin_list · status = pixelgoblin_selftest · shutdown = close stdin
```

## Namespace Changelog

| Date | Change | Reason |
|---|---|---|
| 2026-09-26 | Initial namespace defined, with packs, Goblin Grounds and the VI Builder profile | First forge (session 5) |

---
—Shibbieness
—Claude
