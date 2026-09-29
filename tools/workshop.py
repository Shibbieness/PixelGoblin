#!/usr/bin/env python3
"""The PixelGoblin Workshop helper: reach the working source and the original capsule.

Works in two places:

  * inside the workshop capsule, as build/source/workshop.py, next to
    pixelgoblin-src.zip, with the original capsule in archive/;
  * inside the repository, as tools/workshop.py, with the original capsule in
    dist/archive/.

usage:
  workshop.py unpack DIR            unzip the working source into DIR, ready to run and change
  workshop.py original              list the original capsule's files
  workshop.py original PATH         print one file of the original capsule (e.g. codex/NARRATIVE.md)
  workshop.py original --out DIR    extract the whole original capsule into DIR
  workshop.py find WORDS            find WORDS in file names and text, in the source and the original
  workshop.py check                 confirm both bundles match the fingerprints in META.json

Standard library only. Nothing here changes the capsule or the original.

    —Shibbieness
    —Claude
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGINAL_ROOT = "pixelgoblin-pseudoskill/"
TEXT = (".md", ".py", ".toml", ".json", ".txt", ".html", ".js", ".mjs", ".yaml", ".yml", ".patch")


def places() -> tuple[Path | None, Path | None, Path | None]:
    """(capsule root or None, source zip or None, original archive or None)."""
    if (HERE / "pixelgoblin-src.zip").exists():  # inside the capsule
        cap = HERE.parent.parent
        arch = sorted((cap / "archive").glob("*.skill"))
        return cap, HERE / "pixelgoblin-src.zip", (arch[0] if arch else None)
    root = HERE.parent  # inside the repository
    arch = sorted((root / "dist" / "archive").glob("*.skill"))
    return None, None, (arch[0] if arch else None)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def unpack(dest: Path) -> int:
    cap, src, arch = places()
    if src is None:
        print("unpack works inside the workshop capsule; in the repository you are already unpacked")
        return 1
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        for n in z.namelist():
            if n.startswith("/") or ".." in Path(n).parts:
                raise SystemExit(f"refusing unsafe path {n}")
        z.extractall(dest)
    if arch:  # so tools/package.py workshop can re-forge from the unpacked copy
        (dest / "dist" / "archive").mkdir(parents=True, exist_ok=True)
        shutil.copy2(arch, dest / "dist" / "archive" / arch.name)
        try:  # the session link stays beside the original, never in the source
            sess = json.loads((cap / "META.json").read_text(encoding="utf-8"))["lineage"].get("session")
            if sess:
                (dest / "dist" / "archive" / "lineage.json").write_text(json.dumps({"session": sess}, indent=1) + "\n", encoding="utf-8")
        except (OSError, KeyError, json.JSONDecodeError):
            pass
    print(f"unpacked to {dest}")
    print(f"  run:     cd {dest} && python3 -m pixelgoblin --help")
    print(f"  check:   cd {dest} && PYTHONHASHSEED=0 python3 tests/gate.py --all")
    print(f"  re-forge the workshop after a change: cd {dest} && python3 tools/package.py workshop")
    return 0


def original(args: list[str]) -> int:
    _, _, arch = places()
    if arch is None:
        print("the original capsule is not here (expected archive/*.skill or dist/archive/*.skill)")
        return 1
    with zipfile.ZipFile(arch) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        if not args:
            for n in names:
                print(n[len(ORIGINAL_ROOT):] if n.startswith(ORIGINAL_ROOT) else n)
            print(f"({len(names)} files in {arch.name})")
            return 0
        if args[0] == "--out":
            out = Path(args[1] if len(args) > 1 else "pixelgoblin-pseudoskill-original")
            z.extractall(out)
            print(f"extracted {len(names)} files to {out}")
            return 0
        want = args[0].lstrip("/")
        for cand in (ORIGINAL_ROOT + want, want):
            if cand in names:
                sys.stdout.write(z.read(cand).decode("utf-8", "replace"))
                return 0
        close = [n[len(ORIGINAL_ROOT):] for n in names if want.split("/")[-1] in n][:20]
        print(f"not in the original: {want}" + ("\nclosest: " + "\n  ".join([""] + close) if close else ""))
        return 1


def find(words: str) -> int:
    _, src, arch = places()
    hits = 0
    low = words.lower()
    sources = []
    if src:
        sources.append(("source", src, ""))
    if arch:
        sources.append(("original", arch, ORIGINAL_ROOT))
    if not sources:  # in the repository: search the working tree
        root = HERE.parent
        for p in sorted(root.rglob("*")):
            if p.is_file() and not {".git", "dist", "__pycache__", "refs"} & set(p.relative_to(root).parts) and p.suffix in TEXT:
                t = p.read_text("utf-8", "replace", encoding="utf-8")
                if low in p.name.lower() or low in t.lower():
                    hits += 1
                    print(f"repo      {p.relative_to(root)}")
        return 0 if hits else 1
    for label, zp, strip in sources:
        with zipfile.ZipFile(zp) as z:
            for n in z.namelist():
                if n.endswith("/"):
                    continue
                short = n[len(strip):] if strip and n.startswith(strip) else n
                in_name = low in short.lower()
                in_text = False
                if short.endswith(TEXT) and z.getinfo(n).file_size < 3_000_000:
                    in_text = low in z.read(n).decode("utf-8", "replace").lower()
                if in_name or in_text:
                    hits += 1
                    print(f"{label:9} {short}{'  (name)' if in_name and not in_text else ''}")
    print(f"{hits} files mention '{words}'")
    return 0 if hits else 1


def check() -> int:
    cap, src, arch = places()
    if cap is None:
        print("check works inside the workshop capsule")
        return 1
    meta = json.loads((cap / "META.json").read_text(encoding="utf-8"))
    bad = []
    if src is None or _sha(src) != meta["source_bundle"]["sha256"]:
        bad.append("build/source/pixelgoblin-src.zip does not match META.json")
    if arch is None or _sha(arch) != meta["lineage"]["original_sha256"]:
        bad.append("archive/ original does not match META.json")
    print("\n".join(bad) or "source bundle and original capsule match their fingerprints")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.split("Standard library")[0].strip())
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "unpack":
        return unpack(Path(rest[0] if rest else "pixelgoblin-work"))
    if cmd == "original":
        return original(rest)
    if cmd == "find" and rest:
        return find(" ".join(rest))
    if cmd == "check":
        return check()
    print(f"unknown command: {' '.join(argv)} (try --help)")
    return 2


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):  # a pipe on Windows defaults to cp1252; write UTF-8 everywhere
        _s.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
