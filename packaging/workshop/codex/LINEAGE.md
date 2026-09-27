# LINEAGE — where the PixelGoblin Workshop came from

Tags: #index #complete #lineage #session:5

This page answers "where is the rest of it?". Nothing of the project was dropped to make the workshop fit under the upload limit: the source is packed into one file, and the original capsule is kept whole. Use this page to find anything.

## 1. The original capsule (frozen)

| Field | Value |
|---|---|
| Name | pixelgoblin-pseudoskill |
| Version | {original_version} |
| File | `archive/{archive_name}` |
| Size | {archive_kb} KB, {archive_files} files |
| SHA-256 | `{original_sha256}` |
| Why it is not uploaded | a skill upload accepts at most 200 files; it has {archive_files} |

It is the exact file Mark was given on 2026-09-27. The workshop forge refuses to run if its fingerprint differs, and `workshop.py check` confirms it at any time. Nothing ever writes to it.

How to read it (from the capsule root):

```
python3 build/source/workshop.py original                     # list its files
python3 build/source/workshop.py original codex/NARRATIVE.md  # print one file
python3 build/source/workshop.py original --out /tmp/orig     # unpack all of it
python3 build/source/workshop.py find "war boar"              # search it and the source
```

What only the original has, and where the workshop keeps the same thing:

| In the original | In the workshop |
|---|---|
| `build/source/` (507 loose files) | `build/source/pixelgoblin-src.zip` (one file; same files, SKILL.md names unchanged) |
| `build/config/types/`, `build/config/flavors/` | `src:types/`, `src:flavors/` |
| `build/specs/` | `build/specs/` (same docs) |
| `build/ui/` sources (`src.html`, `widget.src.html`, `grounds.src.html`) | `src:editor/` |
| `build/assets/` build record and gallery | `src:docs/record/pixelgoblin-build-record.html` (gallery inside) |
| `pretune/`, `codex/`, `updates/` | regenerated here for the workshop |

## 2. The sessions

PixelGoblin was built in one continuing working session with Claude (sessions 1 to 5 of the project):

- {session_url}

That session's history is the reasoning behind everything here. `codex/NARRATIVE.md` is the written summary of it; the ADRs in `build/specs/explanation/decisions.md` record each decision. In a claude.ai chat, past chats can be searched for words like "PixelGoblin", "Goblin Grounds" or "Goblintown", but this project's history lives in the session above, not in ordinary chats.

## 3. The published pages (private to Mark)

| Page | Link | Built file here |
|---|---|---|
| Pocket | https://claude.ai/artifact/HRTVjLVPeRsQrRsMHbupqc | `build/ui/pixelgoblin-pocket.html` |
| Goblin Grounds | https://claude.ai/artifact/UhFrDXaQNMqferxmQKQt1D | `build/ui/pixelgoblin-grounds.html` |
| Workbench | https://claude.ai/artifact/EcDDXExxyk7zWFWsLFeZjS | `build/ui/pixelgoblin.html` |
| Build record | https://claude.ai/artifact/HunCxNL28KuxjNxryzYwLt | `src:docs/record/pixelgoblin-build-record.html` |

## 4. The repository

| Field | Value |
|---|---|
| Source commit | `{commit}` |
| Source bundle | `build/source/pixelgoblin-src.zip`, {src_files} files, SHA-256 `{src_sha256}` |
| Author | Shibbieness |

Mark's reference images (`refs/`) are in neither the bundle nor the original, and never will be.

## 5. How the workshop grows

1. `python3 build/source/workshop.py unpack /tmp/pg` (this also puts the original at `dist/archive/` so the re-forge can check it).
2. Change things in `/tmp/pg`, then run the gates.
3. `python3 tools/package.py workshop` makes `dist/pixelgoblin-workshop.skill`, the next version.
4. Upload it in place of this one. The original goes along unchanged every time.

If the workshop ever nears 200 files, the forge stops and says so before anything is uploaded (OPEN_QUESTIONS Q18).

—Shibbieness
—Claude
