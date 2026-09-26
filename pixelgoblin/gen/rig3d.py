"""Views — the front drawing lifted into a 3D model, then seen from anywhere.

The character's front drawing (rig.build_shapes) stays the source of truth.
This module *builds the other views from it*:

  1. LIFT     every 2D shape becomes a solid by a depth rule for its feature:
              a head ellipse becomes an ellipsoid, an arm capsule a 3D capsule,
              a tunic a shell a little deeper than the torso it wraps, a hood a
              dome with an opening for the face, a backpack a box behind the
              back. Eyes, mouths, brows and patterns are DECALS: painted onto
              the front of whatever they were drawn on, so from behind they are
              hidden and from the side they sit on the profile.
  2. VOXELS   the solids fill an N x N x N grid (one voxel per pixel of the
              tier); where solids overlap, the one drawn later in the front
              view wins, exactly as it did in 2D.
  3. VIEWS    an orthographic camera at any yaw (0 front, 90 facing left,
              180 back, 270 facing right) and pitch (0 level, 30 isometric,
              90 top-down) marches each pixel's ray through the grid.

Because every view is a projection of one grid, the views agree the way a
draughtsman's views must: front and side share heights, front and top share
widths, side and top share depths. Gate B18 checks that, and checks that the
front view of the model reproduces the front drawing.

Integer-only and written in the small Python subset tools/transpile_rig.py
carries to JavaScript, so the workbench can rotate a character freely and
draw the same pixels as this file.
"""

from __future__ import annotations

from .rig import CX, D, _bbox, _inside, _snap, isqrt, shade_index

ZC = 512  # depth centre of the design cube: the character stands on z = 512

# sin(d) * 4096 for d = 0..90, rounded once and written down so every
# language uses the same integers
SIN90 = [0, 71, 143, 214, 286, 357, 428, 499, 570, 641, 711, 782, 852, 921, 991, 1060, 1129, 1198, 1266, 1334, 1401,
         1468, 1534, 1600, 1666, 1731, 1796, 1860, 1923, 1986, 2048, 2110, 2171, 2231, 2290, 2349, 2408, 2465, 2522,
         2578, 2633, 2687, 2741, 2793, 2845, 2896, 2946, 2996, 3044, 3091, 3138, 3183, 3228, 3271, 3314, 3355, 3396,
         3435, 3474, 3511, 3547, 3582, 3617, 3650, 3681, 3712, 3742, 3770, 3798, 3824, 3849, 3873, 3896, 3917, 3937,
         3956, 3974, 3991, 4006, 4021, 4034, 4046, 4056, 4065, 4074, 4080, 4086, 4090, 4094, 4095, 4096]

DECAL_FEATS = ["eyes", "eye_whites", "pupils", "highlights", "brows", "mouth", "tongue", "tusks", "pattern", "stitches",
               "straps", "buckle", "necklace", "ear_inner"]
WRAP_FEATS = ["top", "bottom", "sleeves", "bracers", "belt", "scarf", "pauldrons", "pouches"]
HEADWEAR_FEATS = ["headwear", "headwear.large", "goggles", "glasses"]
HELD_DEPTH = {"shield": 14, "lute": 40, "bow": 8, "book": 55, "scroll": 30, "map": 30}


def isin(deg):
    d = deg % 360
    if d <= 90:
        return SIN90[d]
    if d <= 180:
        return SIN90[180 - d]
    if d <= 270:
        return -SIN90[d - 180]
    return -SIN90[360 - d]


def icos(deg):
    return isin(deg + 90)


# ---------------------------------------------------------------- solids
def _solid(kind, a, sh, i, a2):
    """A solid lifted from shape `sh` (index i); a2 is the shape's snapped 2D
    footprint, which a slab extrudes and which decides what drew on what."""
    return {"k": kind, "a": a, "mat": sh.mat, "feat": sh.feat, "layer": sh.z, "idx": i, "bias": sh.bias,
            "k2": sh.kind, "a2": a2, "box": [0, 0, 0, 0, 0, 0], "group": 0}


def _box3(so):
    k = so["k"]
    a = so["a"]
    if k == "ell" or k == "dome":
        return [a[0] - a[3], a[1] - a[4], a[2] - a[5], a[0] + a[3], a[1] + a[4], a[2] + a[5]]
    if k == "cap":
        r = a[6]
        return [min(a[0], a[3]) - r, min(a[1], a[4]) - r, min(a[2], a[5]) - r, max(a[0], a[3]) + r, max(a[1], a[4]) + r, max(a[2], a[5]) + r]
    if k == "pill":
        return [a[0], a[1], a[7] - a[8], a[2], a[3], a[7] + (0 if a[9] else a[8])]
    if k == "wrap":
        b = _bbox(so["k2"], so["a2"])
        return [b[0], b[1], a[2] - a[3], b[2], b[3], a[2] + (0 if a[4] else a[3])]
    b = _bbox(so["k2"], so["a2"])
    sweep = 0
    if len(a) > 2:
        sweep = max(0, max(abs(b[0] - a[2]), abs(b[2] - a[2])) - a[3]) * a[4] // 100
    return [b[0], b[1], a[0], b[2], b[3], a[1] + sweep]


def _profile(off, half, depth):
    """Half-depth of an elliptic profile at `off` from its centre (0 outside)."""
    if half <= 0:
        return 0
    u = off * 4096 // half
    q = 4096 * 4096 - u * u
    if q < 0:
        return -1
    return depth * isqrt(q) // 4096


def _column(so, x, y):
    """The z extents [lo, hi] of solid `so` along the column through (x, y), as
    a flat list of pairs (a dome can have two). Empty if the column misses."""
    k = so["k"]
    a = so["a"]
    if k == "ell":
        u = (x - a[0]) * 4096 // max(1, a[3])
        v = (y - a[1]) * 4096 // max(1, a[4])
        q = 4096 * 4096 - u * u - v * v
        if q < 0:
            return []
        e = a[5] * isqrt(q) // 4096
        return [a[2] - e, a[2] + e]
    if k == "pill":
        if not _inside("R", [a[0], a[1], a[2], a[3], a[4]], x, y):
            return []
        e = _profile(x - a[5], a[6], a[8])
        if e < 0:
            return []
        return [a[7] - e, a[7] if a[9] else a[7] + e]
    if k == "wrap":  # any footprint, rounded front to back like the body it wraps
        if not _inside(so["k2"], so["a2"], x, y):
            return []
        e = _profile(x - a[0], a[1], a[3])
        if e < 0:
            return []
        return [a[2] - e, a[2] if a[4] else a[2] + e]
    if k == "slab":
        if not _inside(so["k2"], so["a2"], x, y):
            return []
        if len(a) > 2:  # swept back: [z0, z1, centre x, straight part, % of the rest]
            sw = max(0, abs(x - a[2]) - a[3]) * a[4] // 100
            return [a[0] + sw, a[1] + sw]
        return [a[0], a[1]]
    if k == "dome":
        cx, cy, cz, rx, ry, rz, th, drop = a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7]
        if y > cy + drop:
            return []
        u = (x - cx) * 4096 // max(1, rx)
        v = (y - cy) * 4096 // max(1, ry)
        q = 4096 * 4096 - u * u - v * v
        if q < 0:
            return []
        eo = rz * isqrt(q) // 4096
        irx, iry, irz = rx - th, ry - th, rz - th
        ei = -1
        if irx > 0 and iry > 0 and irz > 0:
            u2 = (x - cx) * 4096 // irx
            v2 = (y - cy) * 4096 // iry
            q2 = 4096 * 4096 - u2 * u2 - v2 * v2
            if q2 >= 0:
                ei = irz * isqrt(q2) // 4096
        out = []
        # the back half, down to the drop line
        if ei < 0:
            out.append(cz)
        else:
            out.append(cz + ei + 1)
        out.append(cz + eo)
        # the front half: only above the centre line, and open over the face
        if y <= cy and ei < 0:
            out.append(cz - eo)
            out.append(cz - 1)
        return out
    # capsule: tested point by point by voxelize()
    return []


def _in_cap(a, x, y, z):
    x0, y0, z0, x1, y1, z1, r = a[0], a[1], a[2], a[3], a[4], a[5], a[6]
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    px, py, pz = x - x0, y - y0, z - z0
    len2 = dx * dx + dy * dy + dz * dz
    dot = px * dx + py * dy + pz * dz
    if len2 == 0 or dot <= 0:
        return px * px + py * py + pz * pz <= r * r
    if dot >= len2:
        qx, qy, qz = x - x1, y - y1, z - z1
        return qx * qx + qy * qy + qz * qz <= r * r
    return (px * px + py * py + pz * pz) * len2 - dot * dot <= r * r * len2


def front_z(so, x, y, fallback):
    """Nearest z of a solid along the column (x, y), or `fallback`."""
    if so["k"] == "cap":
        b = so["box"]
        z = b[2]
        while z <= b[5]:
            if _in_cap(so["a"], x, y, z):
                return z
            z += 4
        return fallback
    c = _column(so, x, y)
    if len(c) == 0:
        return fallback
    best = c[0]
    i = 0
    while i < len(c):
        if c[i] < best:
            best = c[i]
        i += 2
    return best


def _host(solids, x, y, below):
    """The solid a 2D shape was drawn on: the highest layer under `below`
    whose front footprint contains (x, y)."""
    best = -1
    for j in range(len(solids)):
        so = solids[j]
        if so["layer"] < below and _inside(so["k2"], so["a2"], x, y):
            if best < 0 or so["layer"] > solids[best]["layer"] or (so["layer"] == solids[best]["layer"] and so["idx"] > solids[best]["idx"]):
                best = j
    return best


def lift(shapes, g, px, pose):
    """The front drawing as solids and decals. `shapes` are rig shapes already
    filtered for the tier (rig.visible_shapes)."""
    half = px // 2
    head = -1
    torso = -1
    for i in range(len(shapes)):
        if shapes[i].feat == "head" and head < 0:
            head = i
        if shapes[i].feat == "torso" and torso < 0:
            torso = i
    ha = _snap(shapes[head], half) if head >= 0 else [CX, 300, 200, 200]
    hcx, hcy, hrx, hry = ha[0], ha[1], ha[2], ha[3]
    hrz = hrx * 88 // 100
    ta = _snap(shapes[torso], half) if torso >= 0 else [CX - 120, 400, CX + 120, 700, 40]
    tw = ta[2] - ta[0]
    tcx = (ta[0] + ta[2]) // 2
    thw = tw // 2
    tdz = tw * 38 // 100
    stride = pose.get("stride", 0) * px * 3
    arm_z = ZC - tdz * 50 // 100
    HZ = ZC - tdz * 55 // 100  # the head sits forward of the chest: goblins stoop
    back0 = ZC + tdz
    solids = []
    decals = []
    fronts = []
    for i in range(len(shapes)):
        sh = shapes[i]
        a = _snap(sh, half)
        f = sh.feat
        k = sh.kind
        b = _bbox(k, a)
        cx = (b[0] + b[2]) // 2
        cy = (b[1] + b[3]) // 2
        w = b[2] - b[0]
        h = b[3] - b[1]
        side = -1 if cx < CX else 1
        leg_dz = stride * side
        arm_dz = -stride * side
        so = None
        if f in DECAL_FEATS:
            decals.append({"k2": k, "a2": a, "mat": sh.mat, "feat": f, "layer": sh.z, "idx": i, "bias": sh.bias, "cx": cx, "cy": cy, "group": 0})
            continue
        if f == "head":
            if i == head:
                so = _solid("ell", [a[0], a[1], HZ, a[2], a[3], max(half, a[2] * 88 // 100)], sh, i, a)
            else:
                so = _solid("ell", [a[0], a[1], HZ - a[2] * 10 // 100, a[2], a[3], max(half, a[2] * 88 // 100)], sh, i, a)
        elif f == "torso":
            so = _solid("pill", [a[0], a[1], a[2], a[3], a[4], cx, max(1, w // 2), ZC, max(half, tdz), 0], sh, i, a)
        elif f == "legs" or (f == "bottom" and k == "C"):
            z0, z1 = ZC, ZC + leg_dz
            if a[1] > a[3]:
                z0, z1 = z1, z0
            so = _solid("cap", [a[0], a[1], z0, a[2], a[3], z1, max(half, a[4])], sh, i, a)
        elif f == "feet":
            so = _solid("ell", [a[0], a[1], ZC - a[2] * 40 // 100 + leg_dz, a[2], a[3], max(half, a[2] * 140 // 100)], sh, i, a)
        elif f == "arms" or f == "sleeves" or f == "bracers":
            z0, z1 = arm_z, arm_z + arm_dz
            if a[1] > a[3]:
                z0, z1 = z1, z0
            if k == "C":
                so = _solid("cap", [a[0], a[1], z0, a[2], a[3], z1, max(half, a[4])], sh, i, a)
        elif f == "hands":
            so = _solid("ell", [a[0], a[1], arm_z + arm_dz, a[2], a[3], max(half, a[2])], sh, i, a)
        elif f == "ears" or f == "fins" or f == "earrings":
            t = max(half, hrx * 10 // 100)
            hz = HZ + hrz * 15 // 100
            if f == "fins":
                so = _solid("slab", [hz, hz + 2 * t, hcx, hrx, 45], sh, i, a)
            elif f == "earrings":
                so = _solid("slab", [hz - t - half, hz + t + half, hcx, hrx, 45], sh, i, a)
            else:
                so = _solid("slab", [hz - t, hz + t, hcx, hrx, 45], sh, i, a)  # ears sweep back
        elif f in WRAP_FEATS:
            if f == "pouches":
                so = _solid("pill", [a[0], a[1], a[2], a[3], a[4], cx, max(1, w // 2), ZC - tdz * 60 // 100, max(half, w // 2), 0], sh, i, a)
            elif f == "scarf" and k == "C":
                so = _solid("cap", [a[0], a[1], ZC - tdz * 105 // 100, a[2], a[3], ZC - tdz * 105 // 100, max(half, a[4])], sh, i, a)
            elif k == "R":
                dz = max(half, tdz * (104 + 2 * max(0, sh.z - 20)) // 100)
                front = 1 if w < tw * 85 // 100 and abs(cx - tcx) < w // 4 else 0
                phw = max(thw, max(abs(a[0] - tcx), abs(a[2] - tcx)))
                so = _solid("pill", [a[0], a[1], a[2], a[3], a[4], tcx, phw, ZC, dz, front], sh, i, a)
            elif k == "T":
                phw = max(thw, max(abs(b[0] - tcx), abs(b[2] - tcx)))
                so = _solid("wrap", [tcx, phw, ZC, tdz * 118 // 100, 0], sh, i, a)
            elif k == "E":
                if f == "pauldrons":
                    so = _solid("ell", [a[0], a[1], arm_z - tdz * 30 // 100, a[2], a[3], max(half, a[2])], sh, i, a)
                else:
                    so = _solid("ell", [a[0], a[1], ZC, a[2], a[3], max(half, max(tdz * 115 // 100, a[2] * 70 // 100))], sh, i, a)
            elif k == "C":
                so = _solid("cap", [a[0], a[1], ZC, a[2], a[3], ZC, max(half, a[4])], sh, i, a)
        elif f == "hair":
            if k == "A":
                so = _solid("dome", [a[0], a[1], HZ, a[2], a[3], max(hrz + half, a[2] * 95 // 100), a[4], a[3] * 60 // 100], sh, i, a)
            elif k == "E" and sh.z < 10:
                so = _solid("ell", [a[0], a[1], HZ + hrz * 45 // 100, a[2], a[3], max(half, hrz * 75 // 100)], sh, i, a)
            elif k == "E" and sh.z < 44:
                so = _solid("ell", [a[0], a[1], HZ + hrz * 10 // 100, a[2], a[3], max(half, a[2])], sh, i, a)
            elif k == "E":
                rz = max(a[2], hrz * 70 // 100) if a[2] < a[3] * 50 // 100 else a[2]
                so = _solid("ell", [a[0], a[1], HZ + hrz * 25 // 100, a[2], a[3], max(half, rz)], sh, i, a)
            elif k == "T":
                so = _solid("slab", [HZ - hrz * 55 // 100, HZ + hrz * 55 // 100], sh, i, a)
            elif k == "C" and sh.z < 10:
                so = _solid("cap", [a[0], a[1], HZ + hrz * 60 // 100, a[2], a[3], HZ + hrz * 95 // 100, max(half, a[4])], sh, i, a)
            elif k == "C":
                so = _solid("cap", [a[0], a[1], HZ - hrz * 40 // 100, a[2], a[3], HZ - hrz * 40 // 100, max(half, a[4])], sh, i, a)
        elif f in HEADWEAR_FEATS:
            if k == "A" and a[5] == -1:
                hw = g["headwear"]
                drop = 95 if hw == "hood" or hw == "headscarf" else 60 if hw == "helm" else 20 if hw == "cap" else 0
                so = _solid("dome", [a[0], a[1], HZ, a[2], a[3], max(hrz + 2 * half, a[2] * 97 // 100), a[4], a[3] * drop // 100], sh, i, a)
            elif k == "R" and w >= hrx:
                phw = max(hrx, max(abs(a[0] - hcx), abs(a[2] - hcx)))
                so = _solid("pill", [a[0], a[1], a[2], a[3], a[4], hcx, phw, HZ, max(half, hrz * 108 // 100), 0], sh, i, a)
            elif k == "E" and cy < hcy - hry:
                so = _solid("ell", [a[0], a[1], HZ, a[2], a[3], max(half, a[2])], sh, i, a)
            elif k == "C":
                so = _solid("cap", [a[0], a[1], HZ, a[2], a[3], HZ, max(half, a[4])], sh, i, a)
            elif k == "T" and cy < hcy - hry * 80 // 100:
                so = _solid("slab", [HZ - hrz * 40 // 100, HZ + hrz * 40 // 100], sh, i, a)
            else:
                fronts.append(i)
                continue
        elif f == "back" or f == "back.large":
            if k == "T" and f == "back.large":
                so = _solid("slab", [back0 + half, back0 + half + max(px, tdz * 15 // 100)], sh, i, a)
            elif k == "T":
                so = _solid("slab", [back0 + tw * 13 // 100 - half, back0 + tw * 13 // 100 + half], sh, i, a)
            elif k == "R":
                dz = max(half, w * 35 // 100)
                so = _solid("pill", [a[0], a[1], a[2], a[3], a[4], cx, max(1, w // 2), back0 + dz, dz, 0], sh, i, a)
            elif k == "C":
                so = _solid("cap", [a[0], a[1], back0 + a[4], a[2], a[3], back0 + a[4], max(half, a[4])], sh, i, a)
            elif k == "E" and g["back"] == "fur":
                so = _solid("ell", [a[0], a[1], ZC + tdz * 40 // 100, a[2], a[3], max(tdz * 110 // 100, a[2] * 60 // 100)], sh, i, a)
            elif k == "E":
                so = _solid("ell", [a[0], a[1], back0 + a[2], a[2], a[3], max(half, a[2])], sh, i, a)
        elif f == "held" or f == "held.large":
            kind = g["held"] if side < 0 else g["offhand"]
            pct = HELD_DEPTH.get(kind, 100)
            hz = arm_z + arm_dz - tw * 7 // 100  # just in front of the palm, as in the front drawing
            j = _host(solids, cx, cy, sh.z)
            if j >= 0 and solids[j]["feat"] in ("torso", "top", "bottom", "belt"):
                # held across the body (a shield, a lute): in front of it, never inside it
                depth = min(w, h) * pct // 200 if k != "C" else a[4]
                hz = min(hz, front_z(solids[j], cx, cy, hz) - depth - half)
            if k == "C":
                so = _solid("cap", [a[0], a[1], hz, a[2], a[3], hz, max(half, a[4])], sh, i, a)
            elif k == "R":
                so = _solid("pill", [a[0], a[1], a[2], a[3], a[4], cx, max(1, w // 2), hz, max(half, min(w, h) * pct // 200), 0], sh, i, a)
            elif k == "E":
                so = _solid("ell", [a[0], a[1], hz, a[2], a[3], max(half, min(a[2], a[3]) * pct // 100)], sh, i, a)
            elif k == "T":
                t = max(half, min(w, h) * 8 // 100)
                so = _solid("slab", [hz - t, hz + t], sh, i, a)
            elif k == "A":
                t = max(half, min(w, h) * 10 // 100)
                so = _solid("slab", [hz - t, hz + t], sh, i, a)
        else:
            fronts.append(i)
            continue
        if so is not None:
            so["box"] = _box3(so)
            solids.append(so)
    # front volumes: noses, beards, goggles, flowers... sit on the front
    # surface of what they were drawn on
    for n in range(len(fronts)):
        i = fronts[n]
        sh = shapes[i]
        a = _snap(sh, half)
        k = sh.kind
        b = _bbox(k, a)
        cx = (b[0] + b[2]) // 2
        cy = (b[1] + b[3]) // 2
        w = b[2] - b[0]
        h = b[3] - b[1]
        j = _host(solids, cx, cy, sh.z)
        zs = HZ - hrz * 50 // 100
        if j >= 0:
            zs = front_z(solids[j], cx, cy, zs)
        so = None
        if k == "E":
            rz = max(a[2], a[3]) * 11 // 10 if sh.feat == "nose" else max(half, min(a[2], a[3]) * 60 // 100)
            so = _solid("ell", [a[0], a[1], zs, a[2], a[3], max(half, rz)], sh, i, a)
        elif k == "R":
            so = _solid("pill", [a[0], a[1], a[2], a[3], a[4], cx, max(1, w // 2), zs, max(half, min(w, h) * 30 // 100), 0], sh, i, a)
        elif k == "C":
            so = _solid("cap", [a[0], a[1], zs - half, a[2], a[3], zs - half, max(half, a[4])], sh, i, a)
        elif k == "T":
            t = max(half, min(w, h) * 20 // 100)
            so = _solid("slab", [zs - t, zs + t], sh, i, a)
        else:
            so = _solid("slab", [zs - 2 * half, zs], sh, i, a)
        so["box"] = _box3(so)
        solids.append(so)
    # the order solids fill the grid in: the front drawing's own layering
    order = []
    for i in range(len(solids)):
        j = len(order)
        while j > 0 and (order[j - 1]["layer"] > solids[i]["layer"] or (order[j - 1]["layer"] == solids[i]["layer"] and order[j - 1]["idx"] > solids[i]["idx"])):
            j -= 1
        order.insert(j, solids[i])
    return order, decals


# ---------------------------------------------------------------- moving solids
def _shift2(k2, a2, dx, dy):
    b = list(a2)
    if k2 == "E" or k2 == "A":
        b[0] += dx
        b[1] += dy
    elif k2 == "T":
        b[0] += dx
        b[1] += dy
        b[2] += dx
        b[3] += dy
        b[4] += dx
        b[5] += dy
    else:
        b[0] += dx
        b[1] += dy
        b[2] += dx
        b[3] += dy
    return b


def move(so, dx, dy, dz):
    """A copy of a solid (or decal) moved by (dx, dy, dz)."""
    out = dict(so)
    out["a2"] = _shift2(so["k2"], so["a2"], dx, dy)
    if so.get("cx", None) is not None:
        out["cx"] = so["cx"] + dx
        out["cy"] = so["cy"] + dy
    if so.get("k", None) is None:
        return out
    a = list(so["a"])
    k = so["k"]
    if k == "ell" or k == "dome":
        a[0] += dx
        a[1] += dy
        a[2] += dz
    elif k == "cap":
        a[0] += dx
        a[1] += dy
        a[2] += dz
        a[3] += dx
        a[4] += dy
        a[5] += dz
    elif k == "pill":
        a[0] += dx
        a[1] += dy
        a[2] += dx
        a[3] += dy
        a[5] += dx
        a[7] += dz
    elif k == "wrap":
        a[0] += dx
        a[2] += dz
    else:
        a[0] += dz
        a[1] += dz
        if len(a) > 2:
            a[2] += dx
    out["a"] = a
    out["box"] = _box3(out)
    return out


# ---------------------------------------------------------------- voxels
def voxelize(solids, n, extent):
    """Fill an n*n*n grid (index (z*n + y)*n + x) with solid numbers + 1."""
    if len(solids) > 254:
        raise ValueError("too many solids for one voxel grid (254 at most)")
    vs = extent // n
    grid = bytearray(n * n * n)
    for si in range(len(solids)):
        so = solids[si]
        b = so["box"]
        x0, x1 = max(0, b[0] // vs), min(n - 1, b[3] // vs)
        y0, y1 = max(0, b[1] // vs), min(n - 1, b[4] // vs)
        z0, z1 = max(0, b[2] // vs), min(n - 1, b[5] // vs)
        mark = si + 1
        for yi in range(y0, y1 + 1):
            yc = yi * vs + vs // 2
            for xi in range(x0, x1 + 1):
                xc = xi * vs + vs // 2
                if so["k"] == "cap":
                    for zi in range(z0, z1 + 1):
                        if _in_cap(so["a"], xc, yc, zi * vs + vs // 2):
                            grid[(zi * n + yi) * n + xi] = mark
                    continue
                c = _column(so, xc, yc)
                p = 0
                while p < len(c):
                    lo, hi = c[p], c[p + 1]
                    for zi in range(max(z0, lo // vs), min(z1, hi // vs) + 1):
                        zc = zi * vs + vs // 2
                        if lo <= zc and zc <= hi:
                            grid[(zi * n + yi) * n + xi] = mark
                    p += 2
    return grid


def occupied_box(grid, n):
    """[x0, y0, z0, x1, y1, z1] of the filled voxels, or [] if none."""
    x0, y0, z0, x1, y1, z1 = n, n, n, -1, -1, -1
    for zi in range(n):
        for yi in range(n):
            base = (zi * n + yi) * n
            for xi in range(n):
                if grid[base + xi]:
                    if xi < x0:
                        x0 = xi
                    if xi > x1:
                        x1 = xi
                    if yi < y0:
                        y0 = yi
                    if yi > y1:
                        y1 = yi
                    if zi < z0:
                        z0 = zi
                    if zi > z1:
                        z1 = zi
    if x1 < 0:
        return []
    return [x0, y0, z0, x1, y1, z1]


# ---------------------------------------------------------------- camera
def camera(yaw, pitch):
    """Right, down and forward unit vectors (x4096) of an orthographic camera.
    Yaw 0 looks at the character's face; pitch looks down from above."""
    sy, cy_, sp, cp = isin(yaw), icos(yaw), isin(pitch), icos(pitch)
    r = [cy_, 0, sy]
    d = [sp * sy // 4096, cp, -(sp * cy_ // 4096)]
    f = [-(cp * sy // 4096), sp, cp * cy_ // 4096]
    return r, d, f


def canvas_size(n, pitch):
    """A level or top-down view is n x n; a tilted view is taller, so a
    standing character still fits when seen from above at an angle."""
    if pitch % 90 == 0:
        return n, n
    return n, (n * (abs(icos(pitch)) + abs(isin(pitch))) + 4095) // 4096


def trace(grid, n, extent, yaw, pitch, box):
    """March every pixel's ray through the grid. Returns, per pixel, the solid
    number hit (0 = nothing), the voxel hit (as x, y, z indices) and its
    distance along the ray."""
    vs = extent // n
    W, H = canvas_size(n, pitch)
    r, d, f = camera(yaw, pitch)
    half = extent // 2
    hit = [0] * (W * H)
    vox = [0] * (W * H * 3)
    dist = [0] * (W * H)
    if len(box) == 0:
        return W, H, hit, vox, dist
    # the filled region in design units, for clipping each ray
    lo = [box[0] * vs, box[1] * vs, box[2] * vs]
    hi = [(box[3] + 1) * vs - 1, (box[4] + 1) * vs - 1, (box[5] + 1) * vs - 1]
    step = max(1, vs // 2)
    reach = extent * 2
    for row in range(H):
        v = (2 * row + 1) * vs // 2 - H * vs // 2
        for col in range(W):
            u = (2 * col + 1) * vs // 2 - W * vs // 2
            # origin of this pixel's ray (x4096), then clip t to the filled box
            o = [half * 4096 + u * r[0] + v * d[0], half * 4096 + u * r[1] + v * d[1], half * 4096 + u * r[2] + v * d[2]]
            t0, t1 = -reach, reach
            ok = True
            for ax in range(3):
                if f[ax] == 0:
                    if o[ax] < lo[ax] * 4096 or o[ax] > hi[ax] * 4096:
                        ok = False
                else:
                    ta = (lo[ax] * 4096 - o[ax]) // f[ax]
                    tb = (hi[ax] * 4096 - o[ax]) // f[ax]
                    if ta > tb:
                        ta, tb = tb, ta
                    t0 = max(t0, ta - 1)
                    t1 = min(t1, tb + 1)
            if not ok or t0 > t1:
                continue
            t = t0 - (t0 % step)
            while t <= t1:
                x = (o[0] + t * f[0]) // 4096
                y = (o[1] + t * f[1]) // 4096
                z = (o[2] + t * f[2]) // 4096
                if 0 <= x and x < extent and 0 <= y and y < extent and 0 <= z and z < extent:
                    xi, yi, zi = x // vs, y // vs, z // vs
                    m = grid[(zi * n + yi) * n + xi]
                    if m:
                        p = row * W + col
                        hit[p] = m
                        vox[p * 3] = xi
                        vox[p * 3 + 1] = yi
                        vox[p * 3 + 2] = zi
                        dist[p] = t
                        break
                t += step
    return W, H, hit, vox, dist


def normal(so, x, y, z):
    """Surface normal (x1024 per axis, roughly unit length) at a point of a solid."""
    k = so["k"]
    a = so["a"]
    if k == "cap":
        x0, y0, z0 = a[0], a[1], a[2]
        dx, dy, dz = a[3] - x0, a[4] - y0, a[5] - z0
        len2 = dx * dx + dy * dy + dz * dz
        dot = (x - x0) * dx + (y - y0) * dy + (z - z0) * dz
        qx, qy, qz = x0, y0, z0
        if len2 > 0 and dot >= len2:
            qx, qy, qz = a[3], a[4], a[5]
        elif len2 > 0 and dot > 0:
            qx, qy, qz = x0 + dx * dot // len2, y0 + dy * dot // len2, z0 + dz * dot // len2
        nx, ny, nz = x - qx, y - qy, z - qz
    else:
        b = so["box"]
        hx, hy, hz = max(1, (b[3] - b[0]) // 2), max(1, (b[4] - b[1]) // 2), max(1, (b[5] - b[2]) // 2)
        nx = max(-1024, min(1024, (x - (b[0] + b[3]) // 2) * 1024 // hx))
        ny = max(-1024, min(1024, (y - (b[1] + b[4]) // 2) * 1024 // hy))
        nz = max(-1024, min(1024, (z - (b[2] + b[5]) // 2) * 1024 // hz))
    ln = isqrt(nx * nx + ny * ny + nz * nz)
    if ln == 0:
        return [0, 0, -1024]
    return [nx * 1024 // ln, ny * 1024 // ln, nz * 1024 // ln]


def light_at(so, x, y, z, r, d, f):
    """Light (-1024..1024) for a surface point, lit from the viewer's upper left."""
    nm = normal(so, x, y, z)
    nr = (nm[0] * r[0] + nm[1] * r[1] + nm[2] * r[2]) // 4096
    nd = (nm[0] * d[0] + nm[1] * d[1] + nm[2] * d[2]) // 4096
    nf = (nm[0] * f[0] + nm[1] * f[1] + nm[2] * f[2]) // 4096
    return (-nr * 424 - nd * 566 - nf * 707) // 1024


def decal_at(decals, so, x, y, z):
    """The decal painted at this surface point, or -1. The front drawing's own
    rule, carried into 3D: a decal covers whatever it was drawn over (anything
    on a lower layer), projected from the front onto front-facing surfaces."""
    b = so["box"]
    if z > (b[2] + b[5]) // 2:
        return -1
    best = -1
    for i in range(len(decals)):
        dc = decals[i]
        if dc["group"] == so["group"] and dc["layer"] > so["layer"] and _inside(dc["k2"], dc["a2"], x, y):
            if best < 0 or dc["layer"] > decals[best]["layer"] or (dc["layer"] == decals[best]["layer"] and dc["idx"] > decals[best]["idx"]):
                best = i
    return best


def paint(solids, decals, hit, vox, dist, W, H, n, extent, yaw, pitch, bands, dither, lens):
    """Material and ramp step for every pixel a ray hit."""
    vs = extent // n
    r, d, f = camera(yaw, pitch)
    pix_mat = [""] * (W * H)
    shade = [0] * (W * H)
    for row in range(H):
        for col in range(W):
            p = row * W + col
            m = hit[p]
            if m == 0:
                continue
            so = solids[m - 1]
            x = vox[p * 3] * vs + vs // 2
            y = vox[p * 3 + 1] * vs + vs // 2
            z = vox[p * 3 + 2] * vs + vs // 2
            mat = so["mat"]
            bias = so["bias"]
            dc = decal_at(decals, so, x, y, z)
            if dc >= 0:
                mat = decals[dc]["mat"]
                bias = decals[dc]["bias"]
            pix_mat[p] = mat
            shade[p] = shade_index(light_at(so, x, y, z, r, d, f), lens[mat], bands, dither, col, row, bias)
    return pix_mat, shade


# ---------------------------------------------------------------- Python API (the editor has its own wrapper)
VIEWS = {
    "front": (0, 0), "back": (180, 0),
    "side_left": (90, 0), "side_right": (270, 0),           # sidescroller: facing left / facing right
    "iso_sw": (45, 30), "iso_se": (315, 30),                 # isometric, facing down-left / down-right
    "iso_nw": (135, 30), "iso_ne": (225, 30),                # isometric, facing up-left / up-right
    "top": (0, 90),                                          # straight down
    "three_quarter": (0, 45),                                # top-down RPG camera
}
TURNAROUND = [0, 45, 90, 135, 180, 225, 270, 315]
_GRIDS: dict = {}


def model(data, g, tier, pose=None, extent=None):
    """Solids and decals for a genome at a tier (front drawing, lifted)."""
    from . import rig
    extent = extent or D
    shapes, sigs = rig.visible_shapes(data, g, tier * D // extent, pose)
    solids, decals = lift(shapes, g, extent // tier, pose or {})
    return solids, decals, sigs


def grid_for(solids, n, extent):
    key = (n, extent, repr([(s["k"], s["a"], s["a2"], s["layer"], s["idx"]) for s in solids]))
    if key not in _GRIDS:
        if len(_GRIDS) > 48:
            _GRIDS.clear()
        grid = voxelize(solids, n, extent)
        _GRIDS[key] = (grid, occupied_box(grid, n))
    return _GRIDS[key]


def render_view(data, g, tier, view="front", yaw=None, pitch=None, era=None, pose=None, rim=False, want_map=False,
                extent=None, solids=None, decals=None, sigs=()):
    """The character seen from any direction. `view` names one of VIEWS; `yaw`
    and `pitch` (whole degrees) override it for free rotation."""
    from . import rig
    extent = extent or D
    y0, p0 = VIEWS[view]
    yaw = y0 if yaw is None else yaw
    pitch = p0 if pitch is None else pitch
    era = era or rig.DEFAULT_CHAIN.get(tier, "hd")
    if solids is None:
        solids, decals, sigs = model(data, g, tier, pose, extent)
    grid, box = grid_for(solids, tier, extent)
    W, H, hit, vox, dist = trace(grid, tier, extent, yaw, pitch, box)
    E_ = rig.ERAS[era]
    lens = {k: len(v) for k, v in rig._materials(data, g).items()}
    pix_mat, shade = paint(solids, decals, hit, vox, dist, W, H, tier, extent, yaw, pitch,
                           min(rig.TIER_BANDS[tier], E_["bands"]), E_["dither"] and tier >= 128, lens)
    sig_mats = tuple(sorted({s["mat"] for s in solids if s["feat"] in sigs}))
    spr = rig.finish(data, g, W, H, tier, era, pix_mat, shade, dist, rim, sig_mats)
    if want_map:
        return spr, pix_mat, [solids[m - 1]["feat"] if m else "" for m in hit]
    return spr


def silhouette_extents(spr):
    """[x0, y0, x1, y1] of the opaque pixels."""
    xs = [i % spr.w for i in range(len(spr.px)) if spr.px[i]]
    ys = [i // spr.w for i in range(len(spr.px)) if spr.px[i]]
    return [min(xs), min(ys), max(xs), max(ys)] if xs else []


def orthographic_check(data, g, tier):
    """The draughtsman's rule: front and side share heights, front and top share
    widths, side and top share depths. Compared on the voxel model's own
    projections (no outline), so any disagreement is the renderer's fault."""
    solids, decals, sigs = model(data, g, tier)
    grid, box = grid_for(solids, tier, D)
    out = {}
    for name, (yaw, pitch) in (("front", (0, 0)), ("side", (270, 0)), ("top", (0, 90))):
        W, H, hit, vox, dist = trace(grid, tier, D, yaw, pitch, box)
        cols = [p % W for p in range(W * H) if hit[p]]
        rows = [p // W for p in range(W * H) if hit[p]]
        out[name] = (min(cols), max(cols), min(rows), max(rows)) if cols else None
    return dict(views_agree(out["front"], out["side"], out["top"], tier), front=out["front"], side=out["side"], top=out["top"])


def views_agree(f, s, t, tier):
    """Extents (col0, col1, row0, row1) of front, side (yaw 270) and top views.
    In the side view screen x runs from the back of the model to the front;
    in the top view screen y does too, so they must match column for row."""
    return {
        "heights_agree": f[2:] == s[2:],
        "widths_agree": (f[0], f[1]) == (t[0], t[1]),
        "depths_agree": (s[0], s[1]) == (t[2], t[3]),
    }


def front_agreement(data, g, tier):
    """How well the 3D model's front view reproduces the front drawing:
    silhouette IoU and material agreement, integer percent."""
    from . import rig
    a = rig.render(data, g, tier, want_map=True)[2]
    b = render_view(data, g, tier, "front", want_map=True)[1]
    inter = union = both = agree = 0
    for p, q in zip(a, b):
        inter += p != "" and q != ""
        union += p != "" or q != ""
        if p != "" and q != "":
            both += 1
            agree += p == q
    return {"iou": inter * 100 // max(1, union), "material": agree * 100 // max(1, both)}
