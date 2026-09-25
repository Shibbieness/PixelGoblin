"""Generator registry. Frozen at import: a registry that can be replaced at
runtime is one whose outputs mean nothing (ported from SPIRE's rule)."""

from __future__ import annotations

from types import MappingProxyType

from . import lsystem, mask, parallax, rig, scene, warren

_FRAMES = {
    "mask": mask.generate_frames,
    "lsystem": lsystem.generate_frames,
    "parallax": parallax.generate_frames,
    "rig": rig.generate_frames,
    "scene": scene.generate_frames,
    "warren": warren.generate_frames,
}
REGISTRY = MappingProxyType(_FRAMES)


def frames(tf, seed: int, overrides=None):
    fn = REGISTRY.get(tf.generator)
    if fn is None:
        raise ValueError(f"generator {tf.generator!r} makes sheets/kits, not single sprites; use its own command (autotile, uikit)")
    return fn(tf, seed, overrides)


def sprite(tf, seed: int, overrides=None):
    return frames(tf, seed, overrides)[0]


def stream_paths(tf) -> list[str]:
    if tf.generator == "mask":
        return mask.stream_paths(tf.data)
    if tf.generator == "lsystem":
        return ["grow", "step", "fruit"]
    if tf.generator == "rig":
        return rig.stream_paths()
    if tf.generator == "warren":
        return ["rooms", "loops", "corridors"]
    if tf.generator == "scene":
        return ["clouds", "ridge/0", "ridge/1", "falls", "trees", "platforms", "stalls"] + [f"crowd/{b['name']}" for b in tf.data["crowd"]]
    if tf.generator == "parallax":
        return ["stars"] + [f"layer/{L['name']}" for L in tf.data["layers"]]
    return ["texture"]
