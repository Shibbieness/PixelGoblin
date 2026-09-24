#!/usr/bin/env python3
"""First composite Vanilla Core run: PixelGoblin + QRen Coder.

1. PixelGoblin generates a sprite from a type file and seed.
2. QRen Coder archives the RECIPE (resolved type file + seed + pixel hash),
   not the pixels, as a verified .xqmem archive.
3. QRen decodes and verifies the archive.
4. PixelGoblin regenerates from the recovered recipe; the pixels must match.

A 20x24 goblin costs a few hundred bytes of recipe instead of an image, and
the archive proves itself on read.

usage: composite_qren.py VANILLA_CORE_SRC QREN_REPO [type-id] [seed]
Needs the composite-load fix (patches/vanilla-core-composite-fix.patch).
"""
import json
import sys
import tempfile
from pathlib import Path

vc_src, qren = Path(sys.argv[1]), Path(sys.argv[2])
type_id = sys.argv[3] if len(sys.argv) > 3 else "boc.creature.goblin"
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 7
sys.path.insert(0, str(vc_src))
from vanilla_core.registry import load_flavor  # noqa: E402

pg = load_flavor(Path(__file__).resolve().parent.parent / "flavor.toml")
qr = load_flavor(qren / "flavor.toml")
assert pg.run is not qr.run, "flavors collided: apply the composite-load fix to Vanilla Core"

made = pg.invoke("generate", {"type": type_id, "seed": seed})
recipe = {"type": pg.invoke("validate", {"type": type_id}) | {"data": None}, "seed": seed, "pixel_hash": made["pixel_hash"]}
from pixelgoblin import typefile  # noqa: E402  (available: the flavor put its dir on the path while loading)
recipe["type"]["data"] = typefile.load(type_id).data

with tempfile.TemporaryDirectory() as t:
    out = str(Path(t) / "goblin.qren.png")
    enc = qr.invoke("encode", {"data": recipe, "name": type_id, "output": out, "tags": ["pixelgoblin", "recipe"]})
    xq = enc["paths"]["xqmem"]
    ver = qr.invoke("verify", {"path": xq})
    dec = qr.invoke("decode", {"path": xq})
    back = json.loads(dec["data"]) if isinstance(dec["data"], str) else dec["data"]
    again = pg.invoke("generate", {"type": back["type"]["data"], "seed": back["seed"]})
    size = Path(xq).stat().st_size

print(json.dumps({
    "type": type_id, "seed": seed,
    "archive_bytes": size, "qren_verify_ok": ver["ok"],
    "pixel_hash_original": made["pixel_hash"][:16], "pixel_hash_regenerated": again["pixel_hash"][:16],
    "identical": made["pixel_hash"] == again["pixel_hash"] == back["pixel_hash"],
}, indent=1))
