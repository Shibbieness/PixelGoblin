#!/usr/bin/env python3
"""Falsification — break each behaviour a gate depends on, and prove the gate
notices. Surviving mutants, not passing gates, measure what the suite proves.

Harness safety (SPIRE learned this three times): originals are backed up
BEFORE a mutation is applied, and leftovers are restored ON START — because
SIGKILL cannot be caught, and a harness that can leave the tree broken is
worse than no harness.

Every mutation names the gate that must catch it and why. A mutation with no
rationale is a mutation nobody can evaluate.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / ".falsify_backup"


@dataclass
class Mutation:
    file: str
    old: str
    new: str
    gate: str
    why: str


MUTATIONS = [
    Mutation("pixelgoblin/rng.py", "result = (_rotl((s1 * 5) & M32, 7) * 9) & M32", "result = (_rotl((s1 * 5) & M32, 7) * 7) & M32",
             "B01", "a changed RNG output function must break the published reference vector"),
    Mutation("pixelgoblin/rng.py", 'return sha256(seed16 + b"/" + path.encode("utf-8"))[:16]', 'return sha256(seed16 + path.encode("utf-8"))[:16]',
             "B01", "seed derivation is part of the pixel contract"),
    Mutation("pixelgoblin/gen/mask.py", "    for path, L in layers:\n        rng = S.rng(path)\n", "    shared = S.rng(\"body\")\n    for path, L in layers:\n        rng = shared\n",
             "B01", "one shared stream for all layers is exactly the ADR-008 failure"),
    Mutation("pixelgoblin/typefile.py", "sort_keys=True, separators", "sort_keys=False, separators",
             "B02", "unsorted keys make the hash depend on how a file was written"),
    Mutation("pixelgoblin/typefile.py", "    out = []\n    if isinstance(obj, float):", "    out = []\n    return out\n    if isinstance(obj, float):",
             "B02", "floats would silently enter the integer-only runtime"),
    Mutation("pixelgoblin/typefile.py", "            if ax < 1 or ay < 1 or ax + fw > W - 1 or ay + len(t) > H - 1:", "            if False:",
             "B02", "a template that does not fit must be refused with a reason"),
    Mutation("pixelgoblin/gen/mask.py", "xs = (x, fw - 1 - x) if mirror else (x,)", "xs = (x, fw - 2 - x) if mirror else (x,)",
             "B03", "an off-by-one mirror breaks symmetry and every golden"),
    Mutation("pixelgoblin/tiles/autotile.py", "if not (m & a and m & b):", "if not (m & a or m & b):",
             "B04", "the diagonal rule is what makes 256 masks into 47"),
    Mutation("pixelgoblin/tiles/wfc.py", "    return WfcResult(out, attempts, True, P)", "    return None",
             "B04", "WFC must never return nothing"),
    Mutation("pixelgoblin/convert.py", "if len(hz) != 1 or len(vt) != 1 or len(same) > 3:", "if len(hz) != 1 or len(vt) != 1 or len(same) > 0:",
             "B05", "pixel-perfect cleanup must remove L-corners"),
    Mutation("pixelgoblin/convert.py", "budget = colors - (1 if outline == \"dark\" else 0)", "budget = colors + 4",
             "B05", "the colour budget of a tag profile is a promise"),
    Mutation("pixelgoblin/uikit.py", "sx = inset + (x - inset) % mid", "sx = inset + (x - inset) % (mid + 1)",
             "B06", "a wrong tile period tears the 9-slice edge"),
    Mutation("pixelgoblin/png.py", "+ _chunk(b\"tRNS\", trns)", "",
             "B07", "dropping tRNS loses transparency in every indexed export"),
    Mutation("pixelgoblin/export.py", '"credit": CREDIT, "ml_used": False}', '"credit": CREDIT, "ml_used": False, "made": __import__("time").time_ns()}',
             "B07", "a clock in provenance makes re-exports indistinguishable from changes"),
    Mutation("pixelgoblin/sharecode.py", "if sha256(body)[:2] != chk:", "if False:",
             "B07", "a mistyped share code must not silently decode to another sprite"),
    Mutation("pixelgoblin/verdicts.py", 'return {"verdict": "SOUND" if all(c[1] for c in checks) else "UNSOUND",',
             'return {"ok": True, "verdict": "SOUND" if all(c[1] for c in checks) else "UNSOUND",',
             "B08", "a merged pass/fail field is the conflation the two verdicts exist to prevent"),
    Mutation("pixelgoblin/hazard.py", "    if worst > max_per_sec:", "    if worst > max_per_sec + 10:",
             "B09", "a flash detector with a loosened threshold misses the strobe"),
    Mutation("pixelgoblin/hazard.py", 'nc = "NC" in tokens or any(m in lic for m in NC_MARKERS[1:])', "nc = False",
             "B09", "non-commercial inputs must be caught before a commercial pack ships"),
    Mutation("pixelgoblin/hazard.py", '"Do not ship this animation as-is. Here is what happens: it flashes',
             '"Here is what happens: it flashes', "B09", "the prohibition-first delivery order is tested, not assumed"),
    Mutation("pixelgoblin/brood.py", "src = pa if r % 2 == 0 else pb", "src = pa",
             "B15", "a child that only ever inherits from one parent is not a brood"),
    Mutation("tools/leakguard.py", '    r"co-authored-by:\\s*claude",\n', "",
             "B12", "the leak guard must catch vendor co-author trailers"),
    Mutation("pixelgoblin/gen/lsystem.py", "            d = (d + 1) % 8", "            d = (d + 2) % 8",
             "B03", "the turtle's turn angle is part of every flora golden"),
    Mutation("pixelgoblin/gen/parallax.py", "        s = (t * t * (3 * p - 2 * t) * 1024) // (p * p * p)", "        s = (t * 1024) // p",
             "B03", "the noise interpolation is part of every background golden"),
]


def restore_leftovers() -> int:
    n = 0
    if BACKUP.exists():
        for f in BACKUP.rglob("*"):
            if f.is_file():
                dst = ROOT / f.relative_to(BACKUP)
                shutil.copy2(f, dst)
                n += 1
        shutil.rmtree(BACKUP)
    return n


def main() -> int:
    as_json = "--json" in sys.argv
    restored = restore_leftovers()
    if restored and not as_json:
        print(f"restored {restored} file(s) left by an interrupted run")
    # A mutant "killed" by a gate that was already failing proves nothing: check the baseline first.
    gates = sorted({m.gate for m in MUTATIONS})
    base = subprocess.run([sys.executable, "tests/gate.py", *gates], cwd=ROOT, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONHASHSEED="0"), timeout=900)
    if base.returncode != 0:
        print(json.dumps({"total": len(MUTATIONS), "killed": 0,
                          "survivors": [f"baseline failing — fix these gates before falsifying: {base.stdout[-600:]}"]}))
        return 1
    survivors, results = [], []
    for i, m in enumerate(MUTATIONS):
        path = ROOT / m.file
        src = path.read_text()
        if src.count(m.old) != 1:
            survivors.append(f"#{i} {m.file}: pattern not found exactly once (mutation is stale)")
            continue
        bk = BACKUP / m.file
        bk.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, bk)
        try:
            path.write_text(src.replace(m.old, m.new))
            r = subprocess.run([sys.executable, "tests/gate.py", m.gate], cwd=ROOT, capture_output=True, text=True,
                               env=dict(os.environ, PYTHONHASHSEED="0"), timeout=900)
            killed = r.returncode != 0
        finally:
            shutil.copy2(bk, path)
            shutil.rmtree(BACKUP)
        results.append({"mutation": i, "file": m.file, "gate": m.gate, "killed": killed, "why": m.why})
        if not killed:
            survivors.append(f"#{i} {m.file} ({m.gate}): {m.why}")
        if not as_json:
            print(f"{'killed  ' if killed else 'SURVIVED'} #{i:02d} {m.gate} {m.file}: {m.why}")
    out = {"total": len(MUTATIONS), "killed": sum(r["killed"] for r in results), "survivors": survivors}
    print(json.dumps(out))
    return 0 if not survivors else 1


if __name__ == "__main__":
    sys.exit(main())
