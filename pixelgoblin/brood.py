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


def family(tf, founders: tuple[int, int, int, int], seed: int = 0) -> dict:
    """Three generations from four founder seeds: two couples, their two
    children, and one grandchild. Every child names its parents, so the tree
    is data a game can store; the pictures regenerate from it."""
    a, b, c, d = founders
    kid1, kid2 = seed * 2 + 1001, seed * 2 + 1002
    grand = seed + 2001
    lin1 = lineage(tf, a, b, kid1)
    lin2 = lineage(tf, c, d, kid2)
    # a grandchild inherits whole streams from its parents, who carry their own overrides
    child_overrides = {1: lin1["overrides"], 2: lin2["overrides"]}
    from .rng import Streams, master_seed
    from . import ENGINE_MAJOR
    kid_streams = {1: Streams(master_seed(tf.type_hash, kid1, ENGINE_MAJOR), child_overrides[1]),
                   2: Streams(master_seed(tf.type_hash, kid2, ENGINE_MAJOR), child_overrides[2])}
    pick = Streams(master_seed(tf.type_hash, grand, ENGINE_MAJOR)).rng("brood/pick")
    g_over, g_rec = {}, {}
    for path in gen.stream_paths(tf):
        r = pick.below(100)
        if r < MUTATION_PCT:
            g_rec[path] = "mutation"
            continue
        side = 1 if r % 2 == 0 else 2
        g_over[path] = kid_streams[side].seed(path)
        g_rec[path] = "child 1" if side == 1 else "child 2"
    return {"founders": [a, b, c, d], "children": [{"seed": kid1, "parents": [a, b], "inherited": lin1["inherited"], "overrides": lin1["overrides"]},
                                                   {"seed": kid2, "parents": [c, d], "inherited": lin2["inherited"], "overrides": lin2["overrides"]}],
            "grandchild": {"seed": grand, "parents": [kid1, kid2], "inherited": g_rec, "overrides": g_over}}
