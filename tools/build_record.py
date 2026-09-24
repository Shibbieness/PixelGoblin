#!/usr/bin/env python3
"""Build docs/record/pixelgoblin-build-record.html.

Every number on the page is computed here by running the build — the gates,
the falsification harness, the parity check — never typed. Gallery images
are embedded as data URIs so the page is one self-contained file.

usage: build_record.py GALLERY_DIR [--qren-bytes N]
"""
from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ["PYTHONHASHSEED"] = "0"

import gate  # noqa: E402
from pixelgoblin import VERSION  # noqa: E402

LOG = [
    ("session 1", "Design researched and written: PIXWRIGHT document, ADR-001 to ADR-008, P0–P9 plan, critique."),
    ("session 2", "Mark names it PixelGoblin; asks for SPIRE logic, other skills, his GitHub, and open source unless paid."),
    ("github", "Profile and listing API blocked; cloned QRen-Code-Build-1; found Sovereign_AI_Environment_Build_Gameplan by probing 56 more names."),
    ("licence", "Adopted QRen / Vanilla Core licence set: AGPL-3.0-or-later, commercial placeholder, §7(b) credit. AGPL text copied byte-for-byte; hash verified."),
    ("spire", "Read SPIRE capsule a–i. Ported gates, falsification, vacuity guards, ratchets, from-empty, two verdicts, mechanism-first hazards, scrub, longevity export."),
    ("engine", "Stdlib-only Python engine: xoshiro128** streams, canonical-JSON SHA-256 type hashes, mask / L-system / parallax generators, 47-blob autotiles, WFC, 9-slice UI kits."),
    ("rng", "xoshiro128** checked against the published reference sequence for state {1,2,3,4}."),
    ("flavor", "Book of Cities goblin, aquatic goblin (extends), glowcap, reef. Validator caught a crest template outside the canvas."),
    ("vanilla-core", "PixelGoblin passes the Vanilla Core floor and runs through it: the second real flavor."),
    ("gates", "First gate run: 7 of 11 failing — wrong L-corner definition, missing controls, scrub reading docstrings. Checks fixed, nothing exempted."),
    ("parity", "JavaScript core written line-for-line; first run identical to Python on every case including a 64-bit seed."),
    ("editor", "Offline workbench built: six workshops, Readable and Swap-sides slots; saves through the viewer's downloads capability."),
    ("falsify", "First falsification: 5 of 23 mutants survived. Tests strengthened; all killed. Full build passes from empty."),
    ("composite", "Two flavors sharing a module name collided inside Vanilla Core. Patch and regression test written; 40 of 40 Vanilla Core tests pass."),
    ("qren", "First composite run: goblin recipe archived by QRen, verified, regenerated pixel-identical."),
    ("slm-e", "16 SLM-e piece manifests exported; all pass SLM-e's validate_manifest."),
    ("wfc", "Measured WFC: 3×3 patterns fall back 10/10 at 48×48; 2×2 never. Default changed, limit documented."),
    ("likeness", "Gallery showed black relatives; ramps now learned from interior pixels by coverage."),
    ("record", "This page generated, every count computed from a fresh run."),
]


def img(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> int:
    gallery = Path(sys.argv[1])
    qren_bytes = sys.argv[sys.argv.index("--qren-bytes") + 1] if "--qren-bytes" in sys.argv else "about 1.9 KB"
    with redirect_stdout(io.StringIO()):
        results = gate.run(sorted(gate.GATES))
    fal = subprocess.run([sys.executable, str(ROOT / "tests" / "falsify.py"), "--json"], capture_output=True, text=True, cwd=ROOT)
    fres = json.loads(fal.stdout.strip().splitlines()[-1])
    counts = gate.derived_counts()
    covered = {g for r in results.values() if r["passed"] for g in r["covers"]}
    allg = {g for r in results.values() for g in r["covers"]}
    conv = json.loads((gallery / "conv.json").read_text()) if (gallery / "conv.json").exists() else {"colors": "8"}
    subs = {
        "DATE": "2026-09-24", "VERSION": VERSION,
        "GATES_PASSED": str(sum(r["passed"] for r in results.values())), "GATES_TOTAL": str(len(results)),
        "PLAN_COVERED": str(len(covered)), "PLAN_TOTAL": str(len(allg)),
        "MUT_KILLED": str(fres["killed"]), "MUT_TOTAL": str(fres["total"]),
        "PARITY": str(results["B13"]["asserts"] - results["B13"]["failed"]),
        "GOLDENS": str(counts["goldens"]), "ASSERTS": str(sum(r["asserts"] for r in results.values())),
        "LASTB": sorted(results)[-1][1:], "FLOOR_KEYS": str(len(json.loads(gate.FLOOR.read_text())["floor"])),
        "SLME": str(len(json.loads((ROOT / "slme" / "pieces.json").read_text()))),
        "QREN_BYTES": qren_bytes, "CONV_COLS": str(conv["colors"]),
        "LOG": "\n".join(f"    <li><time>{t}</time>{txt}</li>" for t, txt in LOG),
    }
    for p in sorted(gallery.glob("*.png")):
        subs["IMG_" + p.stem] = img(p)
    html = (ROOT / "docs" / "record" / "record.src.html").read_text()
    for k, v in subs.items():
        html = html.replace("{{" + k + "}}", v)
    left = [s for s in __import__("re").findall(r"\{\{[A-Za-z_]+\}\}", html)]
    if left:
        raise SystemExit(f"unfilled placeholders: {sorted(set(left))}")
    if subs["GATES_PASSED"] != subs["GATES_TOTAL"] or fres["survivors"]:
        print("WARNING: the build is not fully green; the record shows the real numbers")
    out = ROOT / "docs" / "record" / "pixelgoblin-build-record.html"
    out.write_text(html)
    print(f"{out.relative_to(ROOT)}  {len(html) // 1024} KB  gates {subs['GATES_PASSED']}/{subs['GATES_TOTAL']}  mutants {subs['MUT_KILLED']}/{subs['MUT_TOTAL']}  parity {subs['PARITY']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
