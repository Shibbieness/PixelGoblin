"""Generator registry. Frozen at import: a registry that can be replaced at
runtime is one whose outputs mean nothing (ported from SPIRE's rule)."""

from __future__ import annotations

from types import MappingProxyType

from . import lsystem, mask, parallax

_FRAMES = {
    "mask": mask.generate_frames,
    "lsystem": lsystem.generate_frames,
    "parallax": parallax.generate_frames,
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
    if tf.generator == "parallax":
        return ["stars"] + [f"layer/{L['name']}" for L in tf.data["layers"]]
    return ["texture"]
