"""Beasts — mounts built as 3D solids from the start, and riders seated on them.

A goblin is drawn from the front and lifted into 3D (rig3d). A boar or a
wolf is long front to back, so it is built directly as solids in a 2048-unit
cube (twice the goblin's, so a rider fits on top at the same scale). Every
view — side for a sidescroller, isometric, top-down, free rotation — comes
from the same voxel renderer as the goblins, so a rider and a mount always
match in scale, light, outline and era.

A rider is the rider's own lifted model with its legs re-posed astride:
thighs forward along the flanks, shins down, feet in the stirrups.

Integer-only; beast_solids and seat_rider are carried to JavaScript by
tools/transpile_rig.py.
"""

from __future__ import annotations

from .rig3d import _box3, move

EXT = 2048          # the beast (and mounted) design cube
BX = 1024  # centre line
BZ = 1024  # depth centre
BGROUND = 2000


def _pick(rng, options, default):
    if not options:
        return default
    return options[rng.below(len(options))]


def _range(rng, pair):
    lo, hi = pair
    return lo + rng.below(hi - lo + 1) if hi > lo else lo


def genome(data: dict, S) -> dict:
    """What the beast IS. Tier-independent, one stream per concern."""
    bd = data.get("beast", {})
    b = S.rng("b/body")
    g = {"kind": bd.get("kind", "boar")}
    g["length"] = _range(b, tuple(bd.get("length", [820, 960])))
    g["height"] = _range(b, tuple(bd.get("height", [430, 520])))
    g["girth"] = _range(b, tuple(bd.get("girth", [150, 190])))
    h = S.rng("b/head")
    g["head"] = _range(h, tuple(bd.get("head", [120, 150])))
    g["snout"] = _range(h, tuple(bd.get("snout", [60, 100])))
    g["ear"] = _range(h, tuple(bd.get("ear", [40, 70])))
    g["tail"] = _range(h, tuple(bd.get("tail", [60, 120])))
    g["tusks"] = 1 if h.chance(bd.get("tusk_chance", 0)) else 0
    c = S.rng("b/coat")
    g["hair_color"] = _pick(c, bd.get("coat", ["brown"]), "brown")
    g["iris"] = _pick(c, bd.get("iris", ["amber"]), "amber")
    t = S.rng("b/tack")
    g["cloth_a"] = _pick(t, bd.get("blanket", ["red"]), "red")
    g["cloth_b"] = "leather"
    g["saddle"] = 1 if t.chance(bd.get("saddle_chance", 100)) else 0
    team = data.get("team")
    if team:
        g["cloth_a"], g["team"] = team["a"], team["name"]
    return g


def stream_paths() -> list[str]:
    return ["b/body", "b/head", "b/coat", "b/tack"]


# ---------------------------------------------------------------- solids
def _ell(cx, cy, cz, rx, ry, rz, mat, feat, layer, i):
    so = {"k": "ell", "a": [cx, cy, cz, max(1, rx), max(1, ry), max(1, rz)], "mat": mat, "feat": feat, "layer": layer, "idx": i,
          "bias": 0, "k2": "E", "a2": [cx, cy, max(1, rx), max(1, ry)], "box": [0, 0, 0, 0, 0, 0], "group": 1}
    so["box"] = _box3(so)
    return so


def _cap(x0, y0, z0, x1, y1, z1, r, mat, feat, layer, i):
    so = {"k": "cap", "a": [x0, y0, z0, x1, y1, z1, max(1, r)], "mat": mat, "feat": feat, "layer": layer, "idx": i,
          "bias": 0, "k2": "C", "a2": [x0, y0, x1, y1, max(1, r)], "box": [0, 0, 0, 0, 0, 0], "group": 1}
    so["box"] = _box3(so)
    return so


def beast_solids(bg, px, pose, prefix):
    """The beast in the 2048 cube, facing the viewer (-z) at yaw 0. `prefix`
    renames its materials when it shares a palette with a rider."""
    half = px // 2
    s = []
    L, Hh, G = bg["length"], bg["height"], bg["girth"]
    wolf = bg["kind"] == "wolf"
    bob = pose.get("bob", 0) * px
    stride = pose.get("stride", 0) * px * 3
    leg_len = Hh * 50 // 100
    ry = (Hh - leg_len) * 55 // 100 + 20
    cy = BGROUND - leg_len - ry + 40 + bob
    rz = L // 2
    cz = BZ + L * 8 // 100
    fur = prefix + "hair"
    hide = prefix + "fur"
    # body: barrel, and a higher, heavier chest (boar) or a deep narrow chest (wolf)
    s.append(_ell(BX, cy, cz, G, ry, rz, hide, "body", 1, len(s)))
    if wolf:
        s.append(_ell(BX, cy - ry * 10 // 100, cz - rz * 50 // 100, G * 95 // 100, ry * 110 // 100, rz * 45 // 100, hide, "body", 2, len(s)))
    else:
        s.append(_ell(BX, cy - ry * 20 // 100, cz - rz * 45 // 100, G * 105 // 100, ry * 115 // 100, rz * 55 // 100, hide, "body", 2, len(s)))
    top = cy - ry
    # legs: diagonal pairs swing together when walking
    lr = max(half, G * 20 // 100)
    for sx in (-1, 1):
        for fz in (-1, 1):
            z0 = cz - rz * 58 // 100 if fz < 0 else cz + rz * 62 // 100
            dz = stride * sx * fz
            x = BX + sx * G * 62 // 100
            s.append(_cap(x, cy + ry * 30 // 100, z0, x, BGROUND - lr, z0 + dz, lr, hide, "legs", 3, len(s)))
            s.append(_ell(x, BGROUND - lr * 60 // 100, z0 + dz - lr * 30 // 100, lr * 120 // 100, lr * 70 // 100, lr * 140 // 100,
                          prefix + "hoof", "feet", 4, len(s)))
    # head and snout
    hd = bg["head"]
    hz = cz - rz - hd * 35 // 100
    hy = (top + hd * 40 // 100 if wolf else cy - ry * 15 // 100) + bob
    s.append(_ell(BX, hy, hz, hd * 85 // 100, hd, hd * 110 // 100, hide, "head", 5, len(s)))
    sn = bg["snout"] * (150 if wolf else 100) // 100
    sz = hz - hd * 100 // 100 - sn * 30 // 100
    sy = hy + hd * 30 // 100
    s.append(_ell(BX, sy, sz, sn * (45 if wolf else 60) // 100, sn * (40 if wolf else 55) // 100, sn, prefix + "skin", "nose", 6, len(s)))
    s.append(_ell(BX, sy - sn * 5 // 100, sz - sn * 90 // 100, sn * 30 // 100, sn * 25 // 100, max(half, sn * 15 // 100), prefix + "mouth", "nose", 7, len(s)))
    # eyes
    for sx in (-1, 1):
        ex, ey, ez = BX + sx * hd * 45 // 100, hy - hd * 25 // 100, hz - hd * 70 // 100
        s.append(_ell(ex, ey, ez, max(half, hd * 16 // 100), max(half, hd * 14 // 100), max(half, hd * 12 // 100), prefix + "eye_white", "eyes", 8, len(s)))
        s.append(_ell(ex, ey, ez - hd * 6 // 100, max(half, hd * 10 // 100), max(half, hd * 10 // 100), max(half, hd * 10 // 100), prefix + "iris", "eyes", 9, len(s)))
    # ears: tall points (wolf) or floppy flaps (boar)
    er = bg["ear"]
    for sx in (-1, 1):
        x0, y0 = BX + sx * hd * 40 // 100, hy - hd * 80 // 100
        if wolf:
            s.append(_cap(x0, y0, hz, x0 + sx * er * 20 // 100, y0 - er, hz + er * 15 // 100, max(half, er * 25 // 100), hide, "ears", 8, len(s)))
        else:
            s.append(_cap(x0, y0, hz, x0 + sx * er * 80 // 100, y0 - er * 20 // 100, hz + er * 30 // 100, max(half, er * 30 // 100), hide, "ears", 8, len(s)))
    # tusks
    if bg["tusks"]:
        for sx in (-1, 1):
            tx = BX + sx * sn * 45 // 100
            s.append(_cap(tx, sy + sn * 20 // 100, sz - sn * 40 // 100, tx + sx * sn * 25 // 100, sy - sn * 55 // 100, sz - sn * 70 // 100,
                          max(half, sn * 10 // 100), prefix + "teeth", "tusks", 9, len(s)))
    # mane or ruff, and tail
    if wolf:
        s.append(_ell(BX, hy + hd * 60 // 100, hz + hd * 70 // 100, G * 90 // 100, hd * 90 // 100, hd * 80 // 100, fur, "hair", 4, len(s)))
        tl = bg["tail"] * 150 // 100
        s.append(_ell(BX, cy - ry * 10 // 100, cz + rz + tl * 50 // 100, max(half, tl * 25 // 100), max(half, tl * 30 // 100), tl * 60 // 100, fur, "tail", 4, len(s)))
    else:
        n = 5
        for k in range(n):
            z = hz + hd * 60 // 100 + k * rz * 22 // 100
            s.append(_cap(BX, top + ry * 10 // 100 - bob // 2, z, BX, top - bg["ear"] * 60 // 100, z + rz * 8 // 100, max(half, G * 12 // 100), fur, "hair", 4, len(s)))
        tl = bg["tail"]
        s.append(_cap(BX, cy - ry * 40 // 100, cz + rz, BX, cy + ry * 10 // 100, cz + rz + tl, max(half, G * 6 // 100), hide, "tail", 4, len(s)))
    # tack: blanket, saddle, girth strap, stirrups
    if bg["saddle"]:
        s.append(_ell(BX, top + ry * 12 // 100, cz - rz * 15 // 100, G * 104 // 100, ry * 35 // 100, rz * 42 // 100, prefix + "cloth_a", "top", 6, len(s)))
        s.append(_ell(BX, top - 10, cz - rz * 15 // 100, G * 70 // 100, max(half, ry * 18 // 100), rz * 30 // 100, prefix + "leather", "top", 7, len(s)))
        for sx in (-1, 1):
            x = BX + sx * G * 100 // 100
            s.append(_cap(x, top + ry * 10 // 100, cz - rz * 15 // 100, x, cy + ry * 60 // 100, cz - rz * 15 // 100, max(half, px), prefix + "leather", "straps", 7, len(s)))
            s.append(_ell(x, cy + ry * 65 // 100, cz - rz * 15 // 100, max(half, G * 12 // 100), max(half, G * 8 // 100), max(half, G * 10 // 100), prefix + "metal", "held", 8, len(s)))
    return s


def seat(bg):
    """Where a rider's hips sit: [x, y, z] in the 2048 cube."""
    L, Hh = bg["length"], bg["height"]
    leg_len = Hh * 50 // 100
    ry = (Hh - leg_len) * 55 // 100 + 20
    cy = BGROUND - leg_len - ry + 40
    return [BX, cy - ry - 30, BZ + L * 8 // 100 - L // 2 * 15 // 100]


def seat_rider(solids, decals, bg, px):
    """A rider's lifted model, legs re-posed astride, moved onto the saddle."""
    hip_y = 0
    hip_x = 0
    leg_r = px
    for so in solids:
        if so["feat"] == "legs":
            a = so["a"]
            hip_y = max(hip_y, min(a[1], a[4]))
            hip_x = max(hip_x, abs(a[0] - 512))
            leg_r = max(leg_r, a[6])
    at = seat(bg)
    dx, dy, dz = at[0] - 512, at[1] - hip_y, at[2] - 512
    out = []
    for so in solids:
        if so["feat"] == "legs" or so["feat"] == "feet" or (so["feat"] == "bottom" and so["k"] == "cap"):
            continue
        out.append(move(so, dx, dy, dz))
    # astride: thighs forward and out over the flanks, shins down, boots in the stirrups
    G = bg["girth"]
    span = max(hip_x, G + leg_r)
    for sx in (-1, 1):
        hx = at[0] + sx * hip_x
        kx = at[0] + sx * span
        kz = at[2] - leg_r * 5
        ky = at[1] + leg_r * 2
        thigh = {"k": "cap", "a": [hx, at[1], at[2], kx, ky, kz, leg_r * 12 // 10], "mat": "cloth_b", "feat": "bottom", "layer": 14,
                 "idx": 900 + sx, "bias": 0, "k2": "C", "a2": [hx, at[1], kx, ky, leg_r * 12 // 10], "box": [0, 0, 0, 0, 0, 0], "group": 0}
        thigh["box"] = _box3(thigh)
        out.append(thigh)
        fy = ky + leg_r * 5
        shin = {"k": "cap", "a": [kx, ky, kz, kx, fy, kz + leg_r, leg_r], "mat": "skin", "feat": "legs", "layer": 10,
                "idx": 910 + sx, "bias": 0, "k2": "C", "a2": [kx, ky, kx, fy, leg_r], "box": [0, 0, 0, 0, 0, 0], "group": 0}
        shin["box"] = _box3(shin)
        out.append(shin)
        boot = {"k": "ell", "a": [kx, fy, kz, leg_r * 14 // 10, leg_r, leg_r * 2], "mat": "leather", "feat": "feet", "layer": 12,
                "idx": 920 + sx, "bias": 0, "k2": "E", "a2": [kx, fy, leg_r * 14 // 10, leg_r], "box": [0, 0, 0, 0, 0, 0], "group": 0}
        boot["box"] = _box3(boot)
        out.append(boot)
    moved = []
    for dc in decals:
        moved.append(move(dc, dx, dy, dz))
    return out, moved


# ---------------------------------------------------------------- Python API
def streams_for(tf, seed: int, overrides=None):
    from .. import ENGINE_MAJOR
    from ..rng import Streams, master_seed
    return Streams(master_seed(tf.type_hash, seed, ENGINE_MAJOR), overrides)


def render(data, bg, tier, view="side_right", yaw=None, pitch=None, era=None, pose=None, rim=False):
    from . import rig3d
    solids = beast_solids(bg, EXT // tier, pose or {}, "")
    return rig3d.render_view(data, bg, tier, view, yaw, pitch, era, pose, rim, extent=EXT, solids=solids, decals=[])


def mounted_data(rider_data: dict, beast_data: dict, bg: dict) -> dict:
    """One palette for rider and mount: the beast's ramps renamed beast_*."""
    import json
    from .rig import _materials
    data = json.loads(json.dumps(rider_data))
    mats = data["palette"]["materials"]
    for k, v in _materials(beast_data, bg).items():
        mats["beast_" + k] = v
    return data


def mounted(rider_tf, seed, beast_tf, beast_seed, tier, view="side_right", yaw=None, pitch=None, era=None, pose=None, rim=False):
    """A rider on a mount, from any view, at the mount's scale."""
    from . import rig, rig3d
    g = rig.genome(rider_tf.data, rig.streams_for(rider_tf, seed))
    bg = genome(beast_tf.data, streams_for(beast_tf, beast_seed))
    px = EXT // tier
    solids, decals, sigs = rig3d.model(rider_tf.data, g, tier, pose, EXT)
    rider, rdecals = seat_rider(solids, decals, bg, px)
    both = beast_solids(bg, px, pose or {}, "beast_") + rider
    data = mounted_data(rider_tf.data, beast_tf.data, bg)
    return rig3d.render_view(data, g, tier, view, yaw, pitch, era, pose, rim, extent=EXT, solids=_ordered(both), decals=rdecals, sigs=sigs)


def _ordered(solids):
    return sorted(solids, key=lambda s: (s["layer"], s["group"] == 0, s["idx"]))


def generate_frames(tf, seed: int, overrides=None):
    bg = genome(tf.data, streams_for(tf, seed, overrides))
    t = tf.data.get("tier", 64)
    return [render(tf.data, bg, t, pose=p) for p in ({}, {"stride": 1}, {}, {"stride": -1})]
