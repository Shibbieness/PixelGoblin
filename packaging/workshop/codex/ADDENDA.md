<!-- The forge splices each section below into the codex file it names, before that file's signature. -->

@@ NARRATIVE.md

## Session 5, day 2: the workshop

The finished capsule would not upload. Two rules were found by checking it rather than guessing: a skill may hold only one `SKILL.md` (it held five, because the project's own plugin skills were inside it), and a skill may hold at most 200 files (it held 1,058). The first was fixed by renaming the inner skill files to `<name>_SKILL.md` (v1u0p1). The second was confirmed by Mark with a one-file test upload, which worked.

Mark chose not to cut the original down. He asked for a new capsule to work in, with the original kept whole inside it and a way back to it and to the session. So the workshop packs the repository into one file (`build/source/pixelgoblin-src.zip`), keeps the pages and docs loose for reading, regenerates the codex for its own layout, and carries the original byte-for-byte in `archive/`, checked by its fingerprint. A small helper (`workshop.py`) unpacks the source, reads the original, and searches both.

The lesson is the same one the engine keeps teaching: keep one true thing and add views of it. The original is the true record; the workshop is the working view.

@@ OPEN_QUESTIONS.md

## Q18 — Staying under the upload limit as the workshop grows #open-question

- **Known:** a skill upload accepts at most 200 files. The workshop forge stops above 150 (leaving room for Companion Builder additions) and never packages above 200. Most of the project is one file (`build/source/pixelgoblin-src.zip`), so the engine can grow freely; the count grows only with codex pages, pretune outputs and update slots.
- **Proposed:** if it ever gets close, fold the mini-indexes into one file, or move pretune outputs into the source bundle.

## Q19 — Retiring the original #open-question

- **Known:** the original `pixelgoblin-pseudoskill` is kept unchanged in `archive/` and cannot be uploaded as it is.
- **Settles it:** Mark decides whether the workshop fully replaces it, or whether a trimmed original is ever wanted. Until then it rides along untouched.

@@ CALS_NAMESPACE.md

## Workshop component (added with the workshop)

| Component | Type | Cognitive Character | Optimal Task Surface |
|---|---|---|---|
| Workshop (workshop.py, packaging_workshop.py) | module | Re-forging, one version at a time; the original is read, never written | Unpacking to work, looking things up in the original, making the next uploadable version |

Routing: "change PixelGoblin" → unpack, then the normal engine routes and the Gates, then re-forge. "Where did X go?" → `codex/LINEAGE.md`, then `workshop.py find`.
