#!/usr/bin/env python3
"""Publication guard — refuse to publish content that must stay private.

Why this exists rather than a .gitignore:

  * .gitignore only stops *untracked* files. Anything already committed is
    published the moment the remote is public, and rewriting history does
    not recall what was already fetched.
  * .gitignore matches paths. Leaks are content. A file named
    `distribution_model.py` looks like engine code and contains financial
    strategy; a file named `decisions.py` looks like logic and contains the
    decision substrate as Python literals. Both were found by reading, not
    by their names.
  * .gitignore is advisory. `git add -f`, an editor plugin, a packaging
    step, or a tool that does not consult it will all sail straight past.

This scans file *contents* against a denylist, reports every hit with
file:line, and exits non-zero. Wire it into CI and a pre-commit hook so the
rule is enforced by machinery rather than by remembering.

Usage:
    leakguard.py                      scan git-tracked files in cwd
    leakguard.py path [path ...]      scan specific paths (a directory is walked)
    leakguard.py --files-from LIST    scan the paths listed in LIST, one per line
                                      (a long file list does not fit on a Windows
                                      command line)
    leakguard.py --patterns FILE      use a custom denylist (one regex/line)
    leakguard.py --list               print the active denylist and exit

Archives are opened, not skimmed. A .skill, .plugin or .zip is compressed,
so its bytes never match a pattern however much private text is inside — a
built capsule carried a private session link past this guard for exactly that
reason. Every member is scanned (archives inside archives too), hits are
reported as ARCHIVE!member:line, and an archive that cannot be fully opened
(corrupt, encrypted, too large, nested too deep) is itself a finding: a guard
that passes what it could not read has only stopped looking.

Exit codes: 0 clean · 1 leak found · 2 usage error.
"""

from __future__ import annotations

import argparse
import re
import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

# Default denylist. Case-insensitive regexes.
#
# Seeded from the canonical-term list the GILWRIGHT scrub checklist already
# maintains (FORGE.md Appendix B), plus the vendor-attribution and
# session-link markers Vanilla Core's floor rejects. Extend it whenever a
# leak is found — a term list that never grows is a term list nobody is
# checking against reality.
DEFAULT_PATTERNS = [
    # vendor attribution / leaked session links
    r"noreply@anthropic\.com",
    r"claude\.ai/code/session",
    r"claude\.ai/share",
    r"co-authored-by:\s*claude",
    # credentials — never publishable regardless of project
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    r"\bsk-(ant-)?[A-Za-z0-9_\-]{20,}",
    # business-substrate markers: presence means a corpus leaked into code
    r"audience world",
    r"capability node",
    r"spending policy",
    r"owner distribution",
    r"reserve position",
    r"revenue hierarchy",
    r"invariant floor",
    r"sole owner regardless",
]

# Exemptions. A file whose *purpose* is to define or test the prohibition
# must contain the forbidden pattern — the floor cannot reject a vendor
# address without naming one, and its tests cannot prove it works without
# planting one.
#
# This list is deliberately a set of exact paths, never a glob or a
# directory. A blanket exemption is how a guard quietly stops guarding: the
# GILWRIGHT scrub reported "zero canonical-term hits" while its shipped
# product contained the pattern it forbade, because the checklist had no way
# to say "this one is legitimate" and so the claim was simply wrong.
# Recording an exemption explicitly keeps the claim true.
DEFAULT_ALLOWLIST = {
    "tools/leakguard.py",
    "tools/test_leakguard.py",
    # defines the disallowed markers the flavor floor rejects
    "vanilla-core/src/vanilla_core/manifest.py",
    # plants each marker to prove the floor actually rejects it
    "vanilla-core/tests/test_floor.py",
}

_BINARY = re.compile(rb"[\x00]")


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=False, encoding="utf-8"
    )
    if out.returncode != 0:
        raise SystemExit(f"not a git repository: {root}")
    return [root / line for line in out.stdout.split("\n") if line.strip()]


def load_patterns(path: Path | None) -> list[str]:
    if path is None:
        return list(DEFAULT_PATTERNS)
    lines = path.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


# Archive limits. Past any of them the archive is reported, never passed.
MAX_DEPTH = 4                       # archives inside archives
MAX_MEMBER_BYTES = 64 * 1024 * 1024  # one decompressed member
MAX_TOTAL_BYTES = 512 * 1024 * 1024  # everything decompressed from one file


def _scan_text(raw: bytes, regexes: list[re.Pattern]) -> list[tuple[int, str, str]]:
    if _BINARY.search(raw[:8192]):
        # Binary files cannot be reviewed line by line. A database is exactly
        # where a corpus hides, so flag it for a human rather than silently
        # skipping it.
        text = raw.decode("utf-8", errors="ignore")
        return [(0, rx.pattern, "<binary file — inspect manually>") for rx in regexes if rx.search(text)]
    hits = []
    for n, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
        for rx in regexes:
            if rx.search(line):
                hits.append((n, rx.pattern, line.strip()[:120]))
    return hits


def _members(raw: bytes):
    """Yield (name, bytes) for each file in a zip or tar held in memory, or
    None when raw is not an archive. Raises ValueError when it is one that
    cannot be fully read."""
    buf = io.BytesIO(raw)
    if zipfile.is_zipfile(buf):
        try:
            with zipfile.ZipFile(buf) as z:
                infos = [i for i in z.infolist() if not i.is_dir()]
                if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
                    raise ValueError("too large to inspect")
                for i in infos:
                    if i.flag_bits & 0x1:
                        raise ValueError(f"encrypted member {i.filename}")
                    if i.file_size > MAX_MEMBER_BYTES:
                        raise ValueError(f"member {i.filename} too large to inspect")
                    yield i.filename, z.read(i)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError) as e:
            raise ValueError(f"unreadable zip: {e}") from e
        return
    if raw[257:262] == b"ustar" or raw[:2] == b"\x1f\x8b" or raw[:3] == b"BZh" or raw[:6] == b"\xfd7zXZ\x00":
        try:
            with tarfile.open(fileobj=io.BytesIO(raw)) as t:
                total = 0
                for m in t:
                    if not m.isfile():
                        continue
                    total += m.size
                    if m.size > MAX_MEMBER_BYTES or total > MAX_TOTAL_BYTES:
                        raise ValueError(f"member {m.name} too large to inspect")
                    f = t.extractfile(m)
                    yield m.name, f.read() if f else b""
        except tarfile.ReadError:
            if raw[257:262] == b"ustar":
                raise ValueError("unreadable tar")
            # a gzip/bzip2/xz stream that is not a tar: scan it decompressed
            import bz2, gzip, lzma
            try:
                data = {b"\x1f\x8b": gzip.decompress, b"BZ": bz2.decompress, b"\xfd7": lzma.decompress}[raw[:2]](raw)
            except Exception as e:  # noqa: BLE001 — any failure means "could not read"
                raise ValueError(f"unreadable compressed stream: {e}") from e
            yield "<decompressed>", data
        except (tarfile.TarError, OSError, EOFError) as e:
            raise ValueError(f"unreadable tar: {e}") from e
        return
    if raw[:4] == b"PK\x03\x04":
        raise ValueError("unreadable zip: starts like one, but has no readable directory")
    return None


def _allowed_member(name: str, allow: set[str]) -> bool:
    """An exempt path is exempt inside an archive too, but only as that exact
    path: the member is the path, or ends with "/" + the path (a capsule
    carries the repository under a folder). Never a glob, never a directory."""
    name = name.replace("\\", "/")
    return any(name == a or name.endswith("/" + a) for a in allow)


def scan_bytes(raw: bytes, regexes: list[re.Pattern], depth: int = 0, allow: set[str] = frozenset()) -> list[tuple[str, str, str]]:
    """Return (where, pattern, excerpt) for every hit. `where` is a line
    number, or member!...:line inside an archive."""
    try:
        members = list(_members(raw) or [])
        is_archive = _is_archive(raw)
    except ValueError as e:
        return [("", "<archive>", f"<{e} — inspect manually>")]
    if not is_archive:
        return [(str(n) if n else "", pat, ex) for n, pat, ex in _scan_text(raw, regexes)]
    if depth >= MAX_DEPTH:
        return [("", "<archive>", "<archives nested too deep to inspect — inspect manually>")]
    hits = []
    for name, data in members:
        if _allowed_member(name, allow):
            continue
        for where, pat, ex in scan_bytes(data, regexes, depth + 1, allow):
            hits.append((f"!{name}" + (f":{where}" if where and not where.startswith("!") else where), pat, ex))
    return hits


def _is_archive(raw: bytes) -> bool:
    return (zipfile.is_zipfile(io.BytesIO(raw)) or raw[:4] == b"PK\x03\x04" or raw[257:262] == b"ustar" or raw[:2] == b"\x1f\x8b"
            or raw[:3] == b"BZh" or raw[:6] == b"\xfd7zXZ\x00")


def scan_file(path: Path, regexes: list[re.Pattern], allow: set[str] = frozenset()) -> list[tuple[str, str, str]]:
    """Return (where, pattern, excerpt) for every hit in a file, looking
    inside it when it is an archive."""
    try:
        raw = path.read_bytes()
    except (OSError, IsADirectoryError):
        return []
    return scan_bytes(raw, regexes, allow=allow)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="leakguard")
    ap.add_argument("paths", nargs="*", help="files or directories to scan; default = git-tracked")
    ap.add_argument("--files-from", type=Path, help="file listing paths to scan, one per line")
    ap.add_argument("--patterns", type=Path, help="denylist file, one regex per line")
    ap.add_argument("--allow", action="append", default=[], help="repo-relative path to skip")
    ap.add_argument("--list", action="store_true", help="print denylist and exit")
    args = ap.parse_args(argv)

    patterns = load_patterns(args.patterns)
    if args.list:
        for p in patterns:
            print(p)
        return 0

    regexes = [re.compile(p, re.IGNORECASE) for p in patterns]
    root = Path.cwd()
    allow = DEFAULT_ALLOWLIST | set(args.allow)

    named = [Path(p) for p in args.paths]
    if args.files_from:
        named += [Path(l) for l in args.files_from.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not named:
        targets = tracked_files(root)
    else:
        targets = []
        for p in named:
            targets += sorted(q for q in p.rglob("*") if q.is_file() and ".git" not in q.parts) if p.is_dir() else [p]

    findings = 0
    for path in targets:
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()  # --allow is written with /, on Windows too
        except ValueError:
            rel = path.as_posix()
        if rel in allow or not path.is_file():
            continue
        for at, pattern, excerpt in scan_file(path, regexes, allow):
            findings += 1
            where = rel + (at if at.startswith("!") else f":{at}" if at else "")
            print(f"  LEAK  {where}\n        pattern: {pattern}\n        {excerpt}")

    scanned = sum(1 for p in targets if p.is_file())
    if findings:
        print(f"\n  {findings} leak(s) across {scanned} files — PUBLICATION BLOCKED")
        return 1
    print(f"  {scanned} files scanned, no leaks — safe to publish")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):  # a pipe on Windows defaults to cp1252; write UTF-8 everywhere
        _s.reconfigure(encoding="utf-8")
    sys.exit(main())
