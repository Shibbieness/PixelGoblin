#!/usr/bin/env python3
"""Emit PixelGoblin's deterministic pieces as SLM-e manifests (slme/pieces.json).

Every piece here runs with no model. `degrades_to` says what happens if the
piece is unreachable, which is what keeps it a soft pointer, not a hard
dependency.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pixelgoblin import VERSION  # noqa: E402

def piece(pid, ptype, summary, entry, inp, out, degrades):
    return {"id": f"pixelgoblin.{pid}", "type": ptype, "version": VERSION, "source_capsule": "pixelgoblin",
            "summary": summary, "deterministic": True, "needs_model": False, "degrades_to": degrades,
            "cost_class": "free", "invoke": {"lang": "python", "entry": entry},
            "input_schema": inp, "output_schema": out}

PIECES = [
    piece("schema.typefile", "SCHEMA", "Generative type-file schema pixelgoblin/type@1 with plain-English refusals",
          "pixelgoblin.typefile:validate", {"data": "object"}, {"problems": "array"}, "no validation; bad files fail late inside generators"),
    piece("solver.typehash", "SOLVER", "Canonical-JSON SHA-256 identity of a resolved type file",
          "pixelgoblin.typefile:type_hash", {"data": "object"}, {"hash": "string"}, "no stable identity; caches and share codes cannot be trusted"),
    piece("solver.mask", "SOLVER", "Seeded integer mask generator: creatures, items, icons, fungi, with idle frames",
          "pixelgoblin.gen.mask:generate_frames", {"type": "object", "seed": "integer"}, {"frames": "array"}, "hand-drawn or pre-rendered sprites only"),
    piece("solver.lsystem", "SOLVER", "Seeded integer L-system flora generator",
          "pixelgoblin.gen.lsystem:generate_frames", {"type": "object", "seed": "integer"}, {"frames": "array"}, "pre-rendered flora only"),
    piece("solver.parallax", "SOLVER", "Seeded integer parallax backdrop with per-layer scroll factors",
          "pixelgoblin.gen.parallax:generate_layers", {"type": "object", "seed": "integer"}, {"layers": "array"}, "flat or pre-rendered backgrounds"),
    piece("solver.autotile", "SOLVER", "47-tile blob autotile set and map tiling, table derived in code",
          "pixelgoblin.tiles.autotile:build_tileset", {"type": "object", "seed": "integer"}, {"tileset": "object"}, "hand-placed tiles"),
    piece("solver.wfc", "SOLVER", "Integer overlapping WFC with seeded retry and a flagged fallback",
          "pixelgoblin.tiles.wfc:generate", {"sample": "object", "size": "array", "seed": "bytes"}, {"image": "object", "fallback": "boolean"}, "periodic tiling of the sample"),
    piece("solver.nineslice", "SOLVER", "Pixel-exact 9-slice rendering that tiles edges instead of stretching",
          "pixelgoblin.uikit:nine_slice", {"src": "object", "inset": "integer", "w": "integer", "h": "integer"}, {"image": "object"}, "stretched panels with blurred pixels"),
    piece("lexicon.tags", "LEXICON", "Tag taxonomy to conversion profile, inheriting through dotted parents",
          "pixelgoblin.typefile:profile_for", {"tag": "string"}, {"profile": "object"}, "one default profile for every input"),
    piece("constant.palettes", "CONSTANT", "Built-in palettes with recorded colour sources",
          "pixelgoblin.palettes:get", {"name": "string"}, {"colors": "array"}, "palette files supplied by the user"),
    piece("validator.spec", "VALIDATOR", "Spec verdict: does a sprite match its type file (never merged with target)",
          "pixelgoblin.verdicts:spec_verdict", {"type": "object", "sprite": "object"}, {"verdict": "string", "checks": "array"}, "visual review only"),
    piece("validator.target", "VALIDATOR", "Target verdict: can a platform (NES, Game Boy, PICO-8, modern) show the sprite",
          "pixelgoblin.verdicts:target_verdict", {"sprite": "object", "target": "string"}, {"verdict": "string", "checks": "array"}, "discover limits on hardware"),
    piece("validator.flash", "VALIDATOR", "Approximate photosensitive flash check, mechanism-first, labelled UNVERIFIED",
          "pixelgoblin.hazard:flash_check", {"frames": "array", "frame_ms": "integer"}, {"findings": "array"}, "no warning; a certified tool must be used instead"),
    piece("validator.licence", "VALIDATOR", "Licence contamination check for commercial asset packs",
          "pixelgoblin.hazard:licence_check", {"licences": "array", "profile": "string"}, {"findings": "array"}, "manual licence review"),
    piece("solver.sharecode", "SOLVER", "Share codes: engine, type hash prefix, seed and checksum in base32",
          "pixelgoblin.sharecode:encode", {"type_hash": "string", "seed": "integer"}, {"code": "string"}, "share full type files and seeds by hand"),
    piece("solver.rig", "SOLVER", "Character rig: one tier-independent genome drawn at 8 to 256 px with an era look",
          "pixelgoblin.gen.rig:render", {"type": "object", "genome": "object", "tier": "integer", "era": "string"}, {"sprite": "object", "features": "array"},
          "one fixed-size hand-drawn sprite per character"),
    piece("solver.rigchain", "SOLVER", "Build bit chain: the same genome at every tier, with what each tier adds",
          "pixelgoblin.gen.rig:chain", {"type": "object", "seed": "integer"}, {"genome": "object", "chain": "array"}, "tiers drawn separately by hand, with drift"),
    piece("solver.scene", "SOLVER", "Scene composer: layered village with a crowd of real characters at depth tiers",
          "pixelgoblin.gen.scene:generate_frames", {"type": "object", "seed": "integer"}, {"frames": "array"}, "a painted backdrop with no characters"),
    piece("solver.warren", "SOLVER", "Warren dungeons: room graph first, then autotiled floors; every room reachable",
          "pixelgoblin.gen.warren:layout", {"type": "object", "seed": "integer"}, {"grid": "array", "rooms": "array", "edges": "array"}, "hand-built maps"),
    piece("solver.card", "SOLVER", "Character card: the chain, the genome and the LOD ladder on one sheet",
          "pixelgoblin.cards:card", {"type": "object", "seed": "integer"}, {"sprite": "object", "data": "object"}, "a spreadsheet of tier notes"),
    piece("solver.gif", "SOLVER", "Stdlib GIF89a encoder with transparency and looping",
          "pixelgoblin.gif:encode", {"frames": "array", "frame_ms": "integer"}, {"bytes": "bytes"}, "export PNG sheets and animate elsewhere"),
    piece("solver.nameseed", "SOLVER", "A name is a seed: the same name always makes the same character",
          "pixelgoblin.rng:seed_from_name", {"name": "string"}, {"seed": "integer"}, "store numeric seeds"),
    piece("solver.family", "SOLVER", "Three-generation family tree from four founder seeds; pictures regenerate from the tree",
          "pixelgoblin.brood:family", {"type": "object", "founders": "array", "seed": "integer"}, {"tree": "object"}, "unrelated characters"),
    piece("validator.legs", "VALIDATOR", "Legs check: exactly two legs with a gap when drawn alone; items may hide one, never add one",
          "pixelgoblin.gen.rig:legs_check", {"data": "object", "genome": "object", "tier": "integer"}, {"ok": "boolean", "alone": "integer", "shown": "integer"},
          "visual review (the three-leg bug shipped once)"),
    piece("validator.coherence", "VALIDATOR", "Tier coherence: silhouette IoU and material agreement against a style-matched reference",
          "pixelgoblin.gen.rig:coherence", {"data": "object", "genome": "object", "tier": "integer"}, {"iou": "integer", "material": "integer"}, "eyeballing the chain"),
    piece("validator.squint", "VALIDATOR", "Squint: edge contrast per background, detail kept at 1x, and mass",
          "pixelgoblin.readability:squint", {"sprite": "object"}, {"contrast": "object", "detail": "integer", "mass": "integer"}, "sprites that vanish on some ground"),
    piece("gate.build", "GATE", "Eighteen build gates with falsification, vacuity guards and a count ratchet",
          "tests.gate:main", {"gates": "array"}, {"exit": "integer"}, "unverified build"),
]

if __name__ == "__main__":
    out = ROOT / "slme" / "pieces.json"
    out.write_text(json.dumps(PIECES, indent=1) + "\n")
    print(f"{out.relative_to(ROOT)}  {len(PIECES)} pieces")
