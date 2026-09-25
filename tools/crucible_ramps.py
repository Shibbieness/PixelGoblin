#!/usr/bin/env python3
"""Material-true ramps, grounded in CRUCIBLE (tool-time; floats allowed).

What CRUCIBLE decides: how a material catches light. Its `materials` table
gives class and electrical resistivity. Conductors (resistivity below 1e-5
ohm-metres) are metals: they get high-contrast ramps whose top step runs to a
near-white specular glint. Dielectrics (stone, ceramic, wood, polymer) get
soft ramps with no glint, wood a little warmer in its shadows.

What CRUCIBLE does NOT decide: the base colour. The database has no
appearance data, and element CPK colours (in ASSAY) are a molecular-model
convention, not how a metal looks. Base colours below are AUTHORED and
labelled so; the ramp shape is derived.

usage: crucible_ramps.py path/to/crucible.db > flavors/boc/materials.toml
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pixelgoblin.color import oklab_to_rgb, rgb_to_oklab  # noqa: E402

AUTHORED_BASE = {  # CRUCIBLE material id: (key, base colour, authored note)
    1: ("steel", "#7a808a"), 5: ("copper", "#b86a3a"), 6: ("iron", "#5e5a56"), 7: ("silver", "#c4c8ce"),
    8: ("gold", "#d4a830"), 9: ("lead", "#5a5e66"), 38: ("brass", "#c09a40"), 39: ("bronze", "#a0703a"),
    13: ("granite", "#8a8278"), 14: ("marble", "#d8d4cc"), 15: ("brick", "#9a4a34"), 16: ("glass", "#8ac0c8"),
    25: ("oak", "#8a5a30"), 26: ("pine", "#b88a50"), 27: ("bamboo", "#b8a860"),
}
CONDUCTOR = 1e-5  # ohm-metres


def ramp(base_hex: str, metallic: bool, warm: bool) -> list[str]:
    rgb = tuple(int(base_hex[i:i + 2], 16) for i in (1, 3, 5))
    L, a, b = rgb_to_oklab(rgb)
    if metallic:
        steps = [(0.24, 0.45), (0.42, 0.8), (L, 1.0), (min(0.86, L + 0.16), 0.75), (min(0.94, L + 0.30), 0.4)]
    else:
        steps = [(max(0.12, L - 0.26), 1.0), (max(0.15, L - 0.13), 1.0), (L, 1.0), (min(0.95, L + 0.09), 0.9), (min(0.97, L + 0.16), 0.8)]
    out = []
    for i, (l, c) in enumerate(steps):
        da = 0.012 * (2 - i) if warm else 0.0  # warm shadows for wood
        out.append("#%02x%02x%02x" % oklab_to_rgb((l, a * c + da, b * c + da)))
    return out


def main(db: str) -> str:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = {r[0]: r for r in con.execute("SELECT id, name, mat_class, elec_resistivity_ohm_m FROM materials")}
    lines = ["# Material ramps grounded in CRUCIBLE (tools/crucible_ramps.py).",
             "# Shape (contrast, specular glint) is DERIVED from each material's class and",
             "# electrical resistivity in crucible.db; the base colour is AUTHORED.",
             'schema = "pixelgoblin/palette@1"', 'id = "boc.materials.crucible"', "", "[palette.materials_crucible]"]
    for mid, (key, base) in AUTHORED_BASE.items():
        if mid not in rows:
            continue
        _, name, cls, rho = rows[mid]
        metallic = rho is not None and rho < CONDUCTOR
        r = ramp(base, metallic, cls == "wood")
        note = f"crucible #{mid} {name}: {cls}, resistivity {rho} ohm-m -> {'metallic glint' if metallic else 'soft dielectric'}; base {base} authored"
        lines.append(f'{key} = [{", ".join(chr(34) + c + chr(34) for c in r)}]  # {note}')
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(main(sys.argv[1]), end="")
