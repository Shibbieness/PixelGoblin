#!/usr/bin/env python3
"""Forge the PixelGoblin Workshop capsule (pixelgoblin-workshop.skill).

The workshop is the working, uploadable form of the PixelGoblin PseudoSkill.
A skill upload accepts one SKILL.md and at most 200 files; the original capsule
(pixelgoblin-pseudoskill, 1,058 files) cannot be uploaded, and is kept unchanged.

So the workshop:
  * packs the repository into one file, build/source/pixelgoblin-src.zip
    (docs call a path inside it `src:path`);
  * keeps the pages, docs and small config loose for reading;
  * regenerates the codex for its own layout, reusing packaging_capsule.py's
    generators and Forge checklist (that module is not changed by this one);
  * carries the original capsule byte-for-byte in archive/, and refuses to forge
    if its fingerprint differs;
  * stops above a file budget of 150, well under the 200-file upload limit.

usage: packaging_workshop.py [validate <folder>]

    —Shibbieness
    —Claude
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packaging_capsule as pc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NAME = "pixelgoblin-workshop"
VERSION = "v1u0p0"
FORGED = "2026-09-27"
ORIGINAL_NAME = "pixelgoblin-pseudoskill"
ORIGINAL_VERSION = "v1u0p1"
ARCHIVE_NAME = f"{ORIGINAL_NAME}-{ORIGINAL_VERSION}.skill"
ORIGINAL_SHA256 = "38b1561d08b9d7c8f57470f92d663d0e16d2ef3b2f910d288d2098925ed4f66c"  # the file Mark was given, 2026-09-27
ARCHIVE_DEFAULT = ROOT / "dist" / "archive" / ARCHIVE_NAME
# Where the project was built. Kept out of the repository (Mark's rule, enforced by the leak guard):
# it lives in a private file beside the frozen original, and goes only into the capsule's
# LINEAGE.md and META.json. workshop.py unpack writes it back beside the original.
LINEAGE_LOCAL = "lineage.json"
UPLOAD_MAX_FILES = 200
FORGE_BUDGET = 150
UPLOAD_MAX_BYTES = 30 * 1024 * 1024
SRC_ZIP = "build/source/pixelgoblin-src.zip"
SKIP = {".git", "__pycache__", "dist", ".falsify_backup", "out", "refs"}
STAMP = (2026, 9, 27, 0, 0, 0)

# original capsule layout -> workshop layout (applied to generated and copied text)
PATH_MAP = [
    ("build/assets/pixelgoblin-build-record.html", "src:docs/record/pixelgoblin-build-record.html"),
    ("build/assets/gallery/", "the gallery in src:docs/record/pixelgoblin-build-record.html"),
    ("build/config/types/", "src:types/"),
    ("build/config/flavors", "src:flavors"),
    ("build/source/", "src:"),
]
LINEAGE_TAG = ("#lineage", "the original capsule, the session and the pages this workshop descends from")


def _map(text: str) -> str:
    for a, b in PATH_MAP:
        text = text.replace(a, b)
    return text


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _write(p: Path, text: str) -> None:
    pc._write(p, text)


def _copy(a: Path, b: Path) -> None:
    b.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a, b)


# ---------------------------------------------------------------- items
def items() -> list[dict]:
    out = []
    for it in pc.ITEMS:
        w = copy.deepcopy(it)
        for k in ("path", "what", "nav", "not_"):
            w[k] = _map(w[k])
        w["keys"] = [tuple(_map(x) for x in row) for row in w["keys"]]
        out.append(w)
    by = {w["id"]: w for w in out}
    p = by["plugin"]
    p["keys"] = [k if k[0] != "skills/" else ("skills/", "three skills", "packaging/plugin/skills/") for k in p["keys"]]
    p["nav"] = "Built by tools/package.py into dist/pixelgoblin.plugin; gate B21 checks it. A ready-built copy is build/assets/pixelgoblin.plugin."
    k = by["packaging"]
    k["what"] = ("tools/package.py builds dist/pixelgoblin.plugin, the original capsule (tools/packaging_capsule.py) and this workshop "
                 "(tools/packaging_workshop.py). Indexes, tags, graph, changelog and pretune expectations are generated from one table and checked by the Forge validation checklist as code.")
    k["keys"] = k["keys"] + [("packaging_workshop.py", "the workshop forge and its upload checks", "tools/"), ("workshop.py", "unpack, original, find, check", "tools/")]
    k["nav"] = "Run `python3 tools/package.py workshop` (or `all` for the plugin too)."
    out.append(dict(
        id="original-capsule", label="Original capsule (frozen)", path=f"archive/{ARCHIVE_NAME}", st="#asset", ss="#complete", nt=["#session:5", "#lineage"], deps=[],
        what=f"The original PixelGoblin PseudoSkill, {ORIGINAL_NAME} {ORIGINAL_VERSION}, byte-for-byte as Mark was given it. It holds 1,058 files, so it cannot be uploaded; it rides inside the workshop as the frozen reference.",
        keys=[(ARCHIVE_NAME, "the original .skill file", "archive/"), ("README.md", "what it is and how to read it", "archive/"), ("LINEAGE.md", "its layout mapped to the workshop's", "codex/")],
        nav="Read it with `python3 build/source/workshop.py original PATH`; search it with `workshop.py find WORDS`. The forge refuses to run if its SHA-256 changes.",
        not_="Not edited, trimmed or re-forged by anything. Not the working copy (that is the source bundle)."))
    out.append(dict(
        id="workshop", label="Workshop helper and source bundle", path="build/source/workshop.py", st="#module", ss="#complete", nt=["#session:5", "#lineage", "#access"],
        deps=["packaging", "original-capsule"],
        what="The whole repository as one file (build/source/pixelgoblin-src.zip) plus a standard-library helper that unpacks it for work, prints or extracts any file of the original capsule, searches both, and checks both against their fingerprints in META.json.",
        keys=[("pixelgoblin-src.zip", "the repository; every src: path", "build/source/"), ("workshop.py unpack DIR", "a working copy, with the original placed for re-forging", "build/source/workshop.py"),
              ("workshop.py original [PATH]", "read the original", "build/source/workshop.py"), ("workshop.py find WORDS", "search source and original", "build/source/workshop.py"),
              ("workshop.py check", "fingerprints", "build/source/workshop.py")],
        nav="Unpack once per chat to a temporary folder; the capsule folder is read-only. The same helper is src:tools/workshop.py in the repository.",
        not_="Not an editor of this capsule; it only reads. Changes happen in the unpacked copy and come back by re-forging."))
    return out


@contextlib.contextmanager
def as_workshop(its: list[dict]):
    """Point packaging_capsule's generators and checklist at the workshop for the duration."""
    keys = ("ITEMS", "NAME", "CAPSULE_VERSION", "FORGED", "CODEX_FILES", "PROJECT_TAGS")
    saved = {k: getattr(pc, k) for k in keys}
    pc.ITEMS, pc.NAME, pc.CAPSULE_VERSION, pc.FORGED = its, NAME, VERSION, FORGED
    pc.CODEX_FILES = saved["CODEX_FILES"] + [("codex/LINEAGE.md", "Lineage and redirects", "#index", "#complete", ["#session:5", "#lineage"])]
    pc.PROJECT_TAGS = {**saved["PROJECT_TAGS"], LINEAGE_TAG[0]: LINEAGE_TAG[1]}
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(pc, k, v)


# ---------------------------------------------------------------- pieces
def source_bundle(root: Path, dest: Path) -> int:
    """The repository as one deterministic zip. Returns the file count."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root)
            if set(rel.parts) & SKIP or not p.is_file() or p.suffix == ".pyc" or p.name == ".DS_Store":
                continue
            zi = zipfile.ZipInfo(rel.as_posix(), date_time=STAMP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (0o100000 | (p.stat().st_mode & 0o777)) << 16
            z.writestr(zi, p.read_bytes(), compresslevel=9)
            n += 1
    return n


def _splice(text: str, extra: str) -> str:
    """Insert a section before a codex file's closing signature."""
    i = text.rfind("\n---\n—Shibbieness")
    if i == -1:
        i = text.rfind("—Shibbieness")
    return text[:i].rstrip() + "\n\n" + extra.strip() + "\n" + text[i:] if i != -1 else text.rstrip() + "\n\n" + extra.strip() + "\n" + pc._sign()


def _addenda(hand: Path) -> dict[str, str]:
    raw = (hand / "codex" / "ADDENDA.md").read_text()
    parts = re.split(r"^@@ (\S+)\s*$", raw, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def pseudoskill(root: Path, hand: Path) -> str:
    body = _map((root / "packaging" / "capsule" / "PseudoSKILL.md").read_text().split("\n---\n", 1)[1])  # map first; the workshop text below is already right
    body = re.sub(r"^1\. Work in the repository.*$",
                  "1. Work in an unpacked copy: `python3 build/source/workshop.py unpack /tmp/pg` (or Mark's repository). The capsule folder itself is read-only.",
                  body, count=1, flags=re.M)
    body = body.replace("`cd build/source && python3 -m pixelgoblin <command> ...`",
                        "`python3 build/source/workshop.py unpack /tmp/pg`, then `cd /tmp/pg && python3 -m pixelgoblin <command> ...`")
    body = body.replace("7. `python3 tools/package.py all` rebuilds the plugin and this capsule; B21 checks both.",
                        "7. `python3 tools/package.py workshop` re-forges this workshop (`all` rebuilds the plugin too); gate B21 checks both. The original capsule in `archive/` is never rebuilt or replaced.")
    return (hand / "PSEUDOSKILL_PREFACE.md").read_text().rstrip() + "\n\n---\n" + body


def changelog(its: list[dict], src_files: int, sha: str) -> str:
    L = ["# CHANGELOG — PixelGoblin Workshop", "", f"Versions use Mark's VUP format (vMAJORuMINORpPATCH). {VERSION} is the spec's 1.0.0.", "",
         f"## {VERSION} — {FORGED} — FORGE", "",
         "**Summary:** The workshop: PixelGoblin engine v0u1p0 in an uploadable capsule, with the original capsule kept unchanged inside it.", "",
         "**Source:** Compound Build (File Build pass over the repository; Conversation Build pass over sessions 1 to 5 and the upload investigation)", "",
         f"**Lineage:** {ORIGINAL_NAME} {ORIGINAL_VERSION} (`archive/{ARCHIVE_NAME}`, SHA-256 `{sha}`)", "",
         f"**Session:** {pc.SESSION}", "", "**Tags:** #milestone #session:5 #lineage", "", "### Added", ""]
    L += [f"- {it['label']} (`{it['path']}`): {it['what'].split('. ')[0].rstrip('.')}. {it['st']} {it['ss']}" for it in its]
    L += [f"- {label} (`{path}`) {st} {ss}" for path, label, st, ss, _ in pc.CODEX_FILES]
    L += [f"- Pretune scenario `{sid}`: {d}. #test #complete" for sid, d, _ in pc.SCENARIOS]
    L += ["", "### Changed", "",
          f"- From the original's layout: the repository is one bundle (`{SRC_ZIP}`, {src_files} files) instead of loose files; type files are `src:types/` and `src:flavors/`; the gallery is inside the build record. The bundle keeps every `SKILL.md` under its own name, so no renaming is needed.",
          "", "### Deprecated", "", "- Nothing.", "", "### Removed", "", "- Nothing from the project. Loose duplicate copies (the page sources, config copies, the gallery PNGs) are inside the bundle instead.", "",
          "### Fixed", "", "- Uploadability: one `SKILL.md`, header fields under `metadata:`, and a file count far below the 200-file limit (the forge stops above 150).", "",
          "### Notes", "",
          "- The original capsule is carried byte-for-byte and never changed. `codex/LINEAGE.md` maps its layout to this one.",
          "- Validation: packaging_capsule.py's Forge checklist, plus the workshop's own checks (file budget, size, fingerprints, every `src:` pointer resolves). Gate B21 runs them.",
          "- Mark's reference images are not in this capsule and never will be."]
    return "\n".join(L) + "\n" + pc._sign()


def session_link(archive: Path) -> str:
    f = archive.parent / LINEAGE_LOCAL
    try:
        return json.loads(f.read_text()).get("session") or "not recorded in this copy"
    except (OSError, json.JSONDecodeError):
        return "not recorded in this copy (it lives in dist/archive/lineage.json beside the original)"


def lineage(hand: Path, arch: Path, sha: str, src_files: int, src_sha: str, commit: str) -> str:
    with zipfile.ZipFile(arch) as z:
        n = sum(1 for i in z.infolist() if not i.is_dir())
    return (hand / "codex" / "LINEAGE.md").read_text().format(
        original_version=ORIGINAL_VERSION, archive_name=ARCHIVE_NAME, archive_kb=arch.stat().st_size // 1024, archive_files=n,
        original_sha256=sha, session_url=session_link(arch), commit=commit, src_files=src_files, src_sha256=src_sha)


def _commit(root: Path) -> str:
    if not (root / ".git").exists():
        return "unknown (forged from an unpacked copy)"
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True)
    d = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
    return (r.stdout.strip() or "unknown") + (" + uncommitted changes" if d.stdout.strip() else "")


def _readme(title: str, body: str) -> str:
    return f"# {title}\n\n{body.strip()}\n" + pc._sign()


# ---------------------------------------------------------------- forge
def build_workshop(root: Path, dist: Path, archive: Path = ARCHIVE_DEFAULT, archive_sha: str = ORIGINAL_SHA256) -> Path:
    if not archive.exists():
        raise SystemExit(f"the original capsule is not at {archive}; put the exact file there (workshop.py unpack does this for you)")
    sha = _sha(archive)
    if sha != archive_sha:
        raise SystemExit(f"the original capsule's fingerprint changed ({sha[:12]}..., expected {archive_sha[:12]}...); refusing to forge")
    cap = dist / NAME
    if cap.exists():
        shutil.rmtree(cap)
    hand = root / "packaging" / "workshop"
    its = items()
    cap.mkdir(parents=True)
    # router, room, lineage-aware codex prose
    _copy(hand / "workshop_SKILL.md", cap / "SKILL.md")  # named <name>_SKILL.md in the repo, so no capsule ever holds two
    _write(cap / "PseudoSKILL.md", pseudoskill(root, hand))
    add = _addenda(hand)
    for f in ("NARRATIVE.md", "CALS_NAMESPACE.md", "OPEN_QUESTIONS.md"):
        t = _map((root / "packaging" / "capsule" / "codex" / f).read_text())
        _write(cap / "codex" / f, _splice(t, add[f]) if f in add else t)
    _write(cap / "dependencies" / "external_deps.md", _map((root / "packaging" / "capsule" / "dependencies" / "external_deps.md").read_text()))
    _copy(hand / "pretune" / "README.md", cap / "pretune" / "README.md")
    # build/source: the bundle and the helper
    src_zip = cap / SRC_ZIP
    src_files = source_bundle(root, src_zip)
    src_sha = _sha(src_zip)
    _copy(root / "tools" / "workshop.py", cap / "build" / "source" / "workshop.py")
    _write(cap / "build" / "source" / "README.md", _readme("build/source/", f"""
`pixelgoblin-src.zip` is the whole PixelGoblin repository in one file ({src_files} files), so this capsule stays under the 200-file upload limit.
Docs write a path inside it as `src:path`.

```
python3 build/source/workshop.py unpack /tmp/pg     # a working copy
cd /tmp/pg && python3 -m pixelgoblin --help         # run it
python3 build/source/workshop.py find "Goblintown"  # search the source and the original
python3 build/source/workshop.py original codex/NARRATIVE.md
python3 build/source/workshop.py check              # fingerprints
```

The bundle is canonical for current state. Mark's reference images are not in it.
"""))
    # build/ui, build/specs, build/config, build/assets
    for page in pc_pages():
        _copy(root / "editor" / page, cap / "build" / "ui" / page)
    _write(cap / "build" / "ui" / "README.md", _readme("build/ui/", """
The three pages, built and self-contained: `pixelgoblin.html` (Workbench), `pixelgoblin-pocket.html` (Pocket), `pixelgoblin-grounds.html` (Goblin Grounds).
Open one in a browser, or publish it as an artifact with the `downloads` capability. Their sources are `src:editor/` (`src.html`, `widget.src.html`, `grounds.src.html`).
The forge checks each page is byte-identical to the one in the source bundle.
"""))
    for d in sorted((root / "docs").rglob("*.md")):
        _copy(d, cap / "build" / "specs" / d.relative_to(root / "docs"))
    _copy(root / "README.md", cap / "build" / "specs" / "PROJECT_README.md")
    _write(cap / "build" / "specs" / "README.md", _readme("build/specs/", """
The project's docs, in the Diátaxis shape: `tutorials/`, `howto/`, `reference/`, `explanation/` (with the decisions, ADR-001 onward). `PROJECT_README.md` is the repository's front page.
They are copies of `src:docs/`; the forge checks they match. The build record (`src:docs/record/`) is inside the bundle.
"""))
    for f in ("tests/FLOOR.json", "flavor.toml", "packaging/plugin/.claude-plugin/plugin.json"):
        _copy(root / f, cap / "build" / "config" / Path(f).name)
    _write(cap / "build" / "config" / "README.md", _readme("build/config/", """
Small config for reading: `FLOOR.json` (the count ratchet), `flavor.toml` (the Vanilla Core flavor manifest), `plugin.json` (the plugin manifest).
The type files are inside the bundle: `src:types/` (the vanilla pack and tag profiles) and `src:flavors/` (the Book of Cities flavor and every resource pack).
"""))
    _plugin_into(cap / "build" / "assets" / "pixelgoblin.plugin")
    _write(cap / "build" / "assets" / "README.md", _readme("build/assets/", """
`pixelgoblin.plugin` is the PixelGoblin plugin, built from this same source: three skills and nine drawing tools. Install it separately from this skill if you want the tools.
The build record and its gallery are `src:docs/record/pixelgoblin-build-record.html`.
"""))
    # archive: the original, unchanged
    _copy(archive, cap / "archive" / ARCHIVE_NAME)
    _write(cap / "archive" / "README.md", _readme("archive/", f"""
`{ARCHIVE_NAME}` is the original PixelGoblin PseudoSkill ({ORIGINAL_NAME} {ORIGINAL_VERSION}), exactly as Mark was given it.
SHA-256: `{sha}`

It is kept whole and never changed. It holds more files than a skill upload allows, which is why the workshop exists.
Read it without unpacking: `python3 build/source/workshop.py original PATH`. Map of its layout to this one: `codex/LINEAGE.md`.
"""))
    _write(cap / "codex" / "LINEAGE.md", lineage(hand, archive, sha, src_files, src_sha, _commit(root)))
    # generated codex, dependencies, update structure, pretune
    with as_workshop(its):
        pc.update_structure(cap)
        for it in its:
            _write(cap / "codex" / "mini-indexes" / f"{it['id']}.INDEX.md", pc.mini_index(it))
        _write(cap / "codex" / "MASTER_INDEX.md", master_index())
        _write(cap / "codex" / "TAG_REGISTRY.md", pc.tag_registry().replace("# PixelGoblin PseudoSkill", "# PixelGoblin Workshop"))
        _write(cap / "codex" / "CHANGELOG.md", changelog(its, src_files, sha))
        g = pc.dependency_graph()
        _write(cap / "dependencies" / "dependency_graph.json", json.dumps(g, indent=1, ensure_ascii=False))
        _write(cap / "dependencies" / "DEPENDENCY_MAP.md", _map(pc.dependency_map(g)))
        _write(cap / "dependencies" / "internal_deps.md", _map(pc.internal_deps(root)))
        pc.pretune(root, cap)
    for s in (cap / "pretune" / "scenarios").glob("*.json"):
        d = json.loads(s.read_text())
        d["run_from"] = "the unpacked source (python3 build/source/workshop.py unpack DIR)"
        _write(s, json.dumps(d, indent=1, ensure_ascii=False))
    for r in (cap / "pretune" / "results").glob("*.md"):
        _write(r, r.read_text().replace("`build/source/`", "the unpacked source bundle"))
    meta = {"project_name": "PixelGoblin", "codex_name": NAME, "codex_version": "1.0.0", "version": VERSION, "version_format": "VUP",
            "engine_version": "v0u1p0", "forged_date": FORGED, "author": "Shibbieness", "co_author": "Claude", "organization": "M MAOU LLC",
            "compiler_mode": "conversation+file", "build_mode": "compound", "cals_namespace": True, "build_layer_present": True, "pretune_layer_present": True,
            "immutable_core": True, "update_structure_version": "1.0",
            "tags": ["#determinism", "#tier-chain", "#views", "#city", "#parity", "#access", "#packs", "#grounds", "#lineage", "#milestone"],
            "composes_with": ["spire", "slm-e", "book-of-cities", "book-of-cities-compendium-builder", "aether-library-pseudoskill", "crucible", "vi-builder",
                              "gilwright", "dropzone", "cals", "working-with-mark", "pseudoskills-builder", "eexpand"],
            "companion_plugin": "build/assets/pixelgoblin.plugin", "companion_builder_sessions": 0, "last_update": None,
            "lineage": {"original": ORIGINAL_NAME, "original_version": ORIGINAL_VERSION, "original_file": f"archive/{ARCHIVE_NAME}", "original_sha256": sha,
                        "session": session_link(archive)},
            "source_bundle": {"file": SRC_ZIP, "files": src_files, "sha256": src_sha, "commit": _commit(root)},
            "upload": {"max_files": UPLOAD_MAX_FILES, "forge_budget": FORGE_BUDGET, "max_bytes": UPLOAD_MAX_BYTES}}
    _write(cap / "META.json", json.dumps(meta, indent=1, ensure_ascii=False))
    problems = validate(cap)
    if problems:
        raise SystemExit("workshop failed validation:\n  " + "\n  ".join(problems))
    return cap


def pc_pages() -> list[str]:
    return ["pixelgoblin.html", "pixelgoblin-pocket.html", "pixelgoblin-grounds.html"]


def _plugin_into(dest: Path) -> None:
    import package  # tools/package.py
    with tempfile.TemporaryDirectory() as t:
        d = package.build_plugin(Path(t))
        dest.parent.mkdir(parents=True, exist_ok=True)
        package.zip_dir(d, dest)


def master_index() -> str:
    t = pc.master_index().replace("# MASTER INDEX — PixelGoblin PseudoSkill", "# MASTER INDEX — PixelGoblin Workshop")
    t = "\n".join(line for line in t.splitlines() if "_SKILL.md files" not in line) + "\n"
    extra = ["| the original capsule | original-capsule, LINEAGE.md (`workshop.py original`) |",
             "| where did something go / redirects | LINEAGE.md, workshop (`workshop.py find`) |",
             "| unpacking, working and re-forging | workshop, packaging, PseudoSKILL.md §0 |",
             "| the upload limits (one SKILL.md, 200 files) | OPEN_QUESTIONS.md Q18, CHANGELOG.md |",
             "| what `src:` means | SKILL.md (a path inside build/source/pixelgoblin-src.zip) |"]
    anchor = "| how things are checked | gates, specs (gates.md) |"
    return t.replace(anchor, anchor + "\n" + "\n".join(extra))


# ---------------------------------------------------------------- validation
SRC_TOKEN = re.compile(r"src:([A-Za-z0-9_][A-Za-z0-9_./-]*)")
NOTATION = {"path", "path`"}


def _inapplicable(msg: str) -> bool:
    """Checks of the original layout that the workshop replaces with its own (below)."""
    return ("src:" in msg and ("points at" in msg or "graph node" in msg)) or "RENAMED_SKILLS" in msg or "renamed skill file" in msg


def validate(cap: Path) -> list[str]:
    its = items()
    with as_workshop(its):
        P = [p for p in pc.validate(cap) if not _inapplicable(p)]
    files = [p for p in cap.rglob("*") if p.is_file()]
    if len(files) > UPLOAD_MAX_FILES:
        P.append(f"{len(files)} files: a skill upload accepts at most {UPLOAD_MAX_FILES}")
    elif len(files) > FORGE_BUDGET:
        P.append(f"{len(files)} files is over the forge budget of {FORGE_BUDGET} (room is kept for Companion Builder additions; see OPEN_QUESTIONS Q18)")
    size = sum(p.stat().st_size for p in files)
    if size > UPLOAD_MAX_BYTES:
        P.append(f"{size // 1024} KB is over the {UPLOAD_MAX_BYTES // 1048576} MB upload limit")
    P += [f"hidden file {p.relative_to(cap)}: keep the upload plain" for p in files if any(x.startswith(".") for x in p.relative_to(cap).parts)]
    try:
        meta = json.loads((cap / "META.json").read_text())
    except (OSError, json.JSONDecodeError):
        return P + ["META.json does not parse"]
    # the source bundle
    src = cap / SRC_ZIP
    names: set[str] = set()
    if not src.exists():
        P.append(f"{SRC_ZIP} is missing")
    else:
        if _sha(src) != meta.get("source_bundle", {}).get("sha256"):
            P.append(f"{SRC_ZIP} does not match its fingerprint in META.json")
        with zipfile.ZipFile(src) as z:
            names = set(z.namelist())
            for need in ("pixelgoblin/__init__.py", "tools/workshop.py", "tools/packaging_workshop.py", "tests/gate.py", "packaging/workshop/workshop_SKILL.md"):
                if need not in names:
                    P.append(f"the source bundle lacks {need}")
            P += [f"the source bundle must not hold {n}" for n in names if n.startswith("refs/") or "/refs/" in n or "__pycache__" in n]
            for page in pc_pages():
                a = cap / "build" / "ui" / page
                if f"editor/{page}" in names and (not a.exists() or a.read_bytes() != z.read(f"editor/{page}")):
                    P.append(f"build/ui/{page} differs from src:editor/{page}")
            for d in (cap / "build" / "specs").rglob("*.md"):
                rel = d.relative_to(cap / "build" / "specs").as_posix()
                if f"docs/{rel}" in names and d.read_bytes() != z.read(f"docs/{rel}"):
                    P.append(f"build/specs/{rel} differs from src:docs/{rel}")
            helper = cap / "build" / "source" / "workshop.py"
            if not helper.exists() or helper.read_bytes() != z.read("tools/workshop.py"):
                P.append("build/source/workshop.py differs from src:tools/workshop.py")
    # every src: pointer resolves (items, prose, generated codex)
    def resolves(path: str) -> bool:
        path = path.rstrip(".,;:)`")
        return path in names or any(n.startswith(path.rstrip("/") + "/") for n in names)
    for it in its:
        for tok in [it["path"]] + [row[2] for row in it["keys"]]:
            if tok.startswith("src:") and not resolves(tok[4:]):
                P.append(f"{it['id']} points at {tok}, which is not in the source bundle")
    texts = [cap / "SKILL.md", cap / "PseudoSKILL.md"] + sorted((cap / "codex").rglob("*.md")) + sorted((cap / "dependencies").glob("*.md")) + sorted((cap / "build").rglob("README.md"))
    for f in texts:
        if f.exists():
            for tok in set(SRC_TOKEN.findall(f.read_text())):
                if tok not in NOTATION and not resolves(tok):
                    P.append(f"{f.relative_to(cap)} mentions src:{tok}, which is not in the source bundle")
    # the original, unchanged
    lin = meta.get("lineage", {})
    arch = cap / lin.get("original_file", f"archive/{ARCHIVE_NAME}")
    if not arch.exists():
        P.append("the original capsule is missing from archive/")
    else:
        if _sha(arch) != lin.get("original_sha256"):
            P.append("the original capsule does not match its fingerprint: it must never change")
        try:
            with zipfile.ZipFile(arch) as z:
                if f"{ORIGINAL_NAME}/SKILL.md" not in z.namelist():
                    P.append("the archived original is not a pixelgoblin-pseudoskill capsule")
        except zipfile.BadZipFile:
            P.append("the archived original is not a readable capsule")
    if len(list((cap / "archive").glob("*.skill"))) != 1:
        P.append("archive/ must hold exactly one capsule")
    return P


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "validate":
        probs = validate(Path(sys.argv[2]))
        print("\n".join(probs) or "workshop valid")
        sys.exit(1 if probs else 0)
    print(build_workshop(ROOT, ROOT / "dist"))
