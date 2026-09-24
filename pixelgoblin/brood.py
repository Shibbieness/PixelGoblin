"""Brood — seed genealogy. Two parents of the same type make a child that
visibly inherits from both.

Each named stream (body, each part, shading, eyes...) is taken whole from one
parent, chosen by the child's own seed; a small mutation chance gives the
child a fresh stream instead. Because generators read every decision from
named streams, breeding needs no knowledge of what the streams mean.
"""

from __future__ import annotations

from . import ENGINE_MAJOR, gen
from .rng import Streams, master_seed

MUTATION_PCT = 10


def lineage(tf, parent_a: int, parent_b: int, child_seed: int) -> dict:
    child = Streams(master_seed(tf.type_hash, child_seed, ENGINE_MAJOR))
    pa = Streams(master_seed(tf.type_hash, parent_a, ENGINE_MAJOR))
    pb = Streams(master_seed(tf.type_hash, parent_b, ENGINE_MAJOR))
    pick = child.rng("brood/pick")
    overrides, record = {}, {}
    for path in gen.stream_paths(tf):
        r = pick.below(100)
        if r < MUTATION_PCT:
            record[path] = "mutation"
            continue
        src = pa if r % 2 == 0 else pb
        overrides[path] = src.seed(path)
        record[path] = "A" if src is pa else "B"
    return {"overrides": overrides, "inherited": record}


def breed(tf, parent_a: int, parent_b: int, child_seed: int):
    lin = lineage(tf, parent_a, parent_b, child_seed)
    return gen.frames(tf, child_seed, lin["overrides"]), lin["inherited"]
