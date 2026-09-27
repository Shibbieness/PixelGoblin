# PixelGoblin Workshop — PseudoSKILL

The full operational reference. `SKILL.md` is the doorway; this is the room.
Everything here is true of engine v0u1p0 as forged into the workshop on 2026-09-27. Where the source bundle and this file disagree, the source bundle (`build/source/pixelgoblin-src.zip`) wins for current state and this file wins for reasoning.

The ideas are his. Claude is the translator.

## 0. Using the workshop

- **Paths.** `src:path` means `path` inside `build/source/pixelgoblin-src.zip`. After `python3 build/source/workshop.py unpack /tmp/pg` it is `/tmp/pg/path`.
- **Run anything:** unpack once per chat, then `cd /tmp/pg && python3 -m pixelgoblin ...`. The capsule folder itself is read-only; always work in the unpacked copy.
- **Look something up:** `codex/MASTER_INDEX.md` first. If it is not there, `python3 build/source/workshop.py find "words"` searches the source and the original capsule together.
- **The original:** `pixelgoblin-pseudoskill` v1u0p1 is in `archive/`, unchanged. `workshop.py original PATH` prints any of its files. `codex/LINEAGE.md` maps its layout to this one.
- **Improve it:** change the unpacked copy, pass the gates, then `python3 tools/package.py workshop` makes the next workshop version. Never edit the original; never raise the file count past the forge's budget (Q18).
