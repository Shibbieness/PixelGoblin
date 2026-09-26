# VI Builder: integration notes for PixelGoblin

Source: `/root/.claude/skills/synced/ef45a90d-.../vi-builder/`. Read files: SKILL.md, PseudoSKILL.md, META.json, codex/*, and `build/specs/VI_BUILDER_ARCHITECTURE_REFERENCE_v0.3.0.docx` (the authoritative spec, text extracted).
`build/source`, `build/config`, `build/ui` and `build/assets` contain only EMPTY.md. **Nothing is implemented**: Phase 0 (architecture) is complete, Phase 1 has not started, and there is no running registry or API.

## What it is

VI Builder (VIB, "Virtual Intelligence Builder") is Mark's local-first cognitive-infrastructure factory. How it works:
1. Filesystem Sources are wired in and watched through inotify.
2. Their files are extracted (by AiDEA, which is stdlib-only) into typed, tiered **ML Processes**, the atom of the system.
3. The processes are stored in a SQLite **Process Registry**.
4. CALS routes tasks to the processes.
5. Conceptual AIs live in **Cal's Castles** (Walls, Rooms, Gates, Inhabitants, Ancestry, and CASL, which is pending).
6. The UI is a single-file localhost HTML **Cockpit**.

Layers: L1 Filesystem Daemon, L2 Ingestion (AiDEA), L3 ML Process Factory, L4 Process Registry, L5 CALS Composition Engine, L6 Conceptualization, L7 Cockpit.

Tier stack:

| Tier | Name | Formats |
|---|---|---|
| 5 | Interface | 5a Autocomplete, 5b Input Assistance |
| 4 | Inference | 4a Prompt Capsule, 4b RAG Package, 4c Embedding Index, 4d Knowledge Graph, 4e Conceptual Distillation |
| 3 | Model | 3a Fine-tune Dataset, 3b Model Config, 3c LLM Construction Foundation |
| 2 | Application | 2a System Daemon, 2b Start/Stop Job, 2c Installation Wizard |
| 1 | Code | 1a Dependency Refactor, 1b Build Reconstruction, 1c Code Comprehension |
| 0 | Hardware | 0a-0d |

Local-First is load-bearing: anything external must be labelled [OPTIONAL]/[EXTERNAL]. Mark's vocabulary must be used as given, not substituted (Filesystem Source, Ghost Process, Inhabitants, and so on).

## How a project "plugs in"

**VI Builder itself defines no plugin manifest, profile file, YAML or JSON registration format.** A project enters VIB in one of two ways:

1. **As a Filesystem Source (L1).** A local path, FUSE mount or removable media is DEFAULT. SSH, SMB and NFS are OPTIONAL. Connection options per source are:
   - type label (DEFAULT/OPTIONAL/EXTERNAL)
   - Ingest-on-connect toggle
   - Fingerprint, computed automatically: file count, dir-structure hash, extension distribution, median size, sample content hash

   L2 then classifies files by type. The relevant types:

   | file | extractor |
   |---|---|
   | `.py` | AST: docstrings and signatures |
   | `.md` / README | structural |
   | `SKILL.md` / `PseudoSKILL.md` / `.skill` | dedicated capsule extractor: frontmatter, scope, procedures, tag registry |
   | `MASTER_INDEX.md` / `*.INDEX.md` | navigation-map nodes |
   | `.toml` / `.yaml` / `.json` / `.ini` | key-value, with schema inference |
   | `.png` / `.jpg` | metadata only in Phase 1 |

   So a PixelGoblin folder with a PseudoSKILL.md, INDEX files and TOML type files is ingestible as-is. PseudoSkill in gives a Tier 4a Prompt Capsule out, which is then assigned to a Castle.

2. **As an ML Process record in the L4 Registry.** Spec §5.2 lists the fields verbatim:

| Field | Description |
|---|---|
| process_id | UUID + human-readable slug derived from source name. |
| tier | The ML Process tier (0a–5b). Determines what the process is and how it is used. |
| format_type | The specific format within the tier (e.g., Prompt Capsule, Dependency Refactor Process). |
| source_provenance | List of source artifacts: filesystem name, file path, last-known hash, ingest timestamp. |
| build_timestamp | When this process was built. |
| staleness_state | FRESH \| STALE \| GHOST \| CONFLICT — see Section 6.3. |
| content | The actual process content — tier/format-specific. |
| composition_parents | If built by composing other processes: parent process IDs. |
| composition_children | Processes built from this one; Conceptual AIs that consume it. |
| tags | User-assigned and auto-detected tags. |
| usage_history | Timestamps of every invocation. |
| castle_assignments | Which Cal's Castles this process is assigned to, if any. |

Lifecycle: BUILDING, then FRESH, then STALE, GHOST or CONFLICT. Storage: SQLite metadata plus flat-file content under `tier-0/ … tier-5/` directories.
The registry location is unsettled (OQ-06 recommends `~/.local/share/vi-builder/`). No field is marked "required" in the spec. The Factory, not the project, fills in process_id, build_timestamp, staleness and provenance.

Cal's Castle (§8.3) has these components:
- Walls: the scope boundary
- Rooms: named sub-domains
- Gates: interfaces with defined input/output formats
- Inhabitants: the assigned processes
- Ancestry
- CASL: [PENDING OQ-08]

## Examples from sibling capsules (the only concrete registrations in the mount)

**LEXIS**. This is a hand-written "registration profile" in markdown, labelled "(Proposed)". It is copied verbatim from `lexis-pseudoskill/codex/mini-indexes/vi-builder-integration.INDEX.md`:

```
Process ID:       lexis-legal-research-v1
Filesystem source: lexis-pseudoskill/ (this capsule)
Tier:             4 — Inference
Subtype:          Prompt Capsule + RAG-adjacent
Staleness:        HIGH sensitivity — legal sources change frequently
Routing signal:   Legal research, statute lookup, case law, case building
Castle:           Legal Research Castle (proposed)
Inhabitants:      LEXIS (primary); future: Pro Se Document Generator (sibling)
Phase relevance:  Phase 3 (CALS composition engine)
```

LEXIS also mirrors this in its `codex/CALS_NAMESPACE.md` under "## VI Builder Registration Profile". It is the one permitted cross-namespace reference.

**LATTICE/BLOOM Stage 6**. This is a YAML record for daemon-registered SLMs. It is copied verbatim from `lattice/build/bloom/stage-06-vib-registry.md`:

```yaml
process_record:
  id: <slm-id>                           # from SLM spec
  kind: slm
  tier: <pipeline-declared-tier>         # default 2
  name: <slm-name>                       # human-readable
  cognitive_character: <from-CALSProfile>
  optimal_for: <from-CALSProfile>
  weak_for: <from-CALSProfile>
  voice: <from-CALSProfile>
  cals_route: <pipeline-declared-route>
  endpoints:
    - kind: query
      handler: <runtime-handle>
    - kind: status
      handler: <runtime-handle>
    - kind: shutdown
      handler: <runtime-handle>
  origin:
    daemon: lattice-bloom-daemon
    corpus: <corpus-id>
    pipeline: <pipeline-id>
    slm_spec_anchor: <anchor>
  provenance:
    forged: <timestamp>
    base_model: <base>
    training_corpus_size: <token count>
```

BLOOM's rules for this record:
- The endpoints `query`, `status` and `shutdown` are **required**.
- The CALSProfile fields are recommended. Without them the process is "callable but uncharacterized", meaning it can be reached by direct address but not selected by CALS routing.
- A daemon cannot register a process at a tier higher than its own.
- A profile may add required fields.
- Deregistration happens automatically on shutdown.

## "sandbox" / "minigame" / "factory" in VI Builder

- **factory** is core vocabulary: VIB *is* "a local-first cognitive infrastructure factory", and L3 is the "ML Process Factory".
- **sandbox** and **minigame** do not appear anywhere in the vi-builder capsule. "game" appears only as the `updates/gameplans/` slot name.
- The closest fit for a runnable tool is Tier 2a System Daemon or 2b Start/Stop Job. The closest fit for its knowledge is Tier 4a Prompt Capsule, 4b RAG Package or 4e Conceptual Distillation.

## Minimal valid registration for PixelGoblin (proposed, following LEXIS precedent)

Because VIB has no schema, "valid" means following the LEXIS profile convention and supplying the §5.2 identity fields. Put it in PixelGoblin's own `codex/CALS_NAMESPACE.md` (a "## VI Builder Registration Profile" section) and/or `codex/mini-indexes/vi-builder-integration.INDEX.md`:

```
Process ID:        pixelgoblin-pixel-art-v1
Filesystem source: pixelgoblin/ (local path, DEFAULT; Ingest-on-connect: on)
Tier:              4 — Inference (4a Prompt Capsule from PseudoSKILL.md; 4b RAG Package over type files)
                   [runtime generator, if exposed: 2a System Daemon]
Format type:       Prompt Capsule
Staleness:         MEDIUM — type files / palettes change with the game
Routing signal:    pixel art, sprite, tile, background, palette, material ramp, tagged type file
Castle:            Pixel Art Castle (proposed); Rooms: backgrounds, characters, objects, palettes
Tags:              #vi-builder-tier4 #cals-namespace
Phase relevance:   Phase 1 (Tier 4 Prompt Capsule ingest)
```

If it is registered as a runtime service in LATTICE style, add `kind`, `endpoints` (query/status/shutdown) and an `origin` block. Also mark any network path [OPTIONAL].
