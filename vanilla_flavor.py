"""PixelGoblin as a Vanilla Core flavor.

An adapter, not a rewrite: maps the Vanilla Core contract
``run(capability, params)`` onto PixelGoblin's public API and returns plain
JSON-serialisable dicts. Images come back as base64 PNG so any host can use
them without a file system. Nothing here imports ``vanilla_core`` — the
flavor stays independently usable.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pixelgoblin import CREDIT, VERSION, gen, sharecode, typefile, uikit, verdicts  # noqa: E402
from pixelgoblin.convert import convert_rgba  # noqa: E402
from pixelgoblin.png import decode as png_decode  # noqa: E402
from pixelgoblin.tiles import autotile  # noqa: E402

CAPABILITIES = ("generate", "convert", "autotile", "uikit", "validate", "share", "verdict", "self-test")


class FlavorError(Exception):
    """Bad input to this adapter, kept distinct from engine errors."""


def _require(params: dict, key: str):
    if key not in params:
        raise FlavorError(f"capability requires --param {key}=<value>")
    return params[key]


def _png(s, scale=1) -> str:
    return base64.b64encode(s.png_bytes(scale)).decode("ascii")


def _type(params):
    t = _require(params, "type")
    return typefile.from_dict(t, "<param>") if isinstance(t, dict) else typefile.load(t)


def _generate(p):
    tf = _type(p)
    seed = int(p.get("seed", 0))
    frames = gen.frames(tf, seed)
    return {"type_id": tf.id, "type_hash": tf.type_hash, "seed": seed, "pixel_hash": frames[0].pixel_hash(),
            "share": sharecode.encode(tf.type_hash, seed), "license": tf.license,
            "frames_png_base64": [_png(f, int(p.get("scale", 1))) for f in frames]}


def _convert(p):
    raw = base64.b64decode(_require(p, "png_base64"))
    w, h, rgba = png_decode(raw)
    s, rep = convert_rgba(w, h, rgba, _require(p, "tag"), p.get("overrides"))
    return {"png_base64": _png(s, int(p.get("scale", 1))), "report": rep, "pixel_hash": s.pixel_hash()}


def _autotile(p):
    tf = _type(p)
    sheet, masks = autotile.build_tileset(tf, int(p.get("seed", 0)))
    out = {"tileset_png_base64": _png(sheet), "tile": tf.data["tile"], "columns": autotile.COLS, "blob_masks": masks}
    if "grid" in p:
        out["tiles"] = autotile.map_tiles(p["grid"])
    return out


def _uikit(p):
    tf = _type(p)
    k = uikit.build_kit(tf, int(p.get("seed", 0)))
    return {"atlas_png_base64": _png(k["atlas"]), "kit": k["kit"]}


def _validate(p):
    try:
        tf = _type(p)
        return {"ok": True, "type_id": tf.id, "type_hash": tf.type_hash}
    except typefile.TypeFileError as e:
        return {"ok": False, "problems": e.problems}


def _share(p):
    if "code" in p:
        return sharecode.decode(p["code"])
    tf = _type(p)
    return {"code": sharecode.encode(tf.type_hash, int(p.get("seed", 0)))}


def _verdict(p):
    tf = _type(p)
    s = gen.sprite(tf, int(p.get("seed", 0)))
    return {"spec": verdicts.spec_verdict(tf, s), "target": verdicts.target_verdict(s, p.get("target", "modern"))}


def _self_test(p):
    tf = typefile.load("vanilla.creature.blob")
    a, b = gen.sprite(tf, 42), gen.sprite(tf, 42)
    return {"ok": a.pixel_hash() == b.pixel_hash(), "version": VERSION, "credit": CREDIT,
            "pixel_hash": a.pixel_hash(), "share": sharecode.encode(tf.type_hash, 42)}


_DISPATCH = {"generate": _generate, "convert": _convert, "autotile": _autotile, "uikit": _uikit,
             "validate": _validate, "share": _share, "verdict": _verdict, "self-test": _self_test}


def run(capability: str | None = None, params: dict | None = None) -> dict:
    """Vanilla Core entrypoint. See CAPABILITIES for what `capability` accepts."""
    params = params or {}
    capability = capability or "self-test"
    handler = _DISPATCH.get(capability)
    if handler is None:
        raise FlavorError(f"unknown capability {capability!r}; expected one of {list(_DISPATCH)}")
    return handler(params)
