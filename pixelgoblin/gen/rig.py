"""Rig generator — one character genome, rendered at any resolution tier.

The problem it solves: a character must still be *that character* at 8x8 and
at 256x256. Hand-made pixel art does this by redrawing. A generator does it by
separating two things:

  GENOME   what the character IS — height, head, ears, nose, hair, outfit,
           items, expression — decoded once from named random streams.
           It never looks at the tier.
  RENDER   how the character is DRAWN at a tier — which features exist at this
           size (the level-of-detail ladder), how many shade bands, outline
           width, and which era palette limit applies.

All geometry lives in a 1024x1024 design space and is rasterised with integer
tests only (ellipses, rounded rectangles, capsules, triangles, rings), sampled
at pixel centres. Every tier in the chain (8, 16, 32, 64, 128, 256) divides
1024, so pixel centres land on whole design units. No floating point anywhere,
so the JavaScript port can match it bit for bit.

Identity rules (pixel-art practice, made mechanical):
  * features below their tier on the LOD ladder are omitted, not smeared;
  * identity features (ears, staff, spear, horns) are "snapped": their
    thickness never drops below one pixel, so they survive at small tiers;
  * the gap between the legs never closes: leg spacing grows to at least one
    pixel of clear space at every tier (the three-leg bug cannot come back);
  * animation moves in whole pixels at every tier.
"""

from __future__ import annotations

from .. import ENGINE_MAJOR
from ..rng import Streams, master_seed
from ..sprite import TRANSPARENT, Sprite, hex_to_rgba

TIERS = (8, 16, 32, 64, 128, 256)
D = 1024          # design space
CX = 512          # centre line
GROUND = 1000     # bottom of the feet

BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# ---------------------------------------------------------------- the ladder
# feature id -> smallest tier at which it is drawn. This table IS the
# level-of-detail ladder; the character card prints it per character.
LOD = {
    "body": 8, "head": 8, "ears": 8, "legs": 8, "arms": 8, "torso": 8,
    "held.large": 8, "headwear.large": 8, "back.large": 8,
    "top": 8, "bottom": 8, "hair": 8, "feet": 8,
    "eyes": 16, "held": 16, "headwear": 16, "back": 16,
    "beard": 16, "belt": 16, "glasses": 16, "goggles": 16, "pauldrons": 16, "fins": 16,
    "mouth": 32, "nose": 32, "hands": 32, "sleeves": 32, "scarf": 32, "earrings": 32, "buckle": 32,
    "brows": 64, "eye_whites": 64, "ear_inner": 64, "necklace": 64, "tusks": 64, "pouches": 64, "bracers": 64,
    "tongue": 64, "flowers": 64, "straps": 64,
    "pupils": 128, "highlights": 128, "pattern": 128, "stitches": 128, "fur_tufts": 128, "nails": 128,
}

# shade bands per tier, and eras (the "bit" styles) and their colour budgets
TIER_BANDS = {8: 1, 16: 2, 32: 3, 64: 4, 128: 5, 256: 5}
# Tier stylisation: small sprites exaggerate the head and eyes (the chibi rule
# every hand-made sprite chain uses) so identity survives. Percentage points
# added to head size, and % added to eye size, per tier.
TIER_HEAD = {8: 14, 16: 8, 32: 4, 64: 1, 128: 0, 256: 0}
TIER_EYE = {8: 0, 16: 40, 32: 25, 64: 10, 128: 0, 256: 0}
ERAS = {
    "8-bit":  {"max_colors": 3,   "bands": 2, "dither": False, "outline": "plain",  "why": "NES-class: 3 colours + transparent per sprite"},
    "16-bit": {"max_colors": 15,  "bands": 3, "dither": False, "outline": "selout", "why": "SNES/Genesis-class: 15 colours + transparent per sprite palette"},
    "32-bit": {"max_colors": 31,  "bands": 4, "dither": False, "outline": "selout", "why": "GBA/PS1-class 2D: larger palettes, smoother ramps"},
    "hd":     {"max_colors": 255, "bands": 5, "dither": True,  "outline": "selout", "why": "modern HD pixel art: full ramps, ordered dithering"},
}
DEFAULT_CHAIN = {8: "8-bit", 16: "16-bit", 32: "16-bit", 64: "32-bit", 128: "hd", 256: "hd"}

# ---------------------------------------------------------------- vocabulary
AGES = {  # height range, head % of height, leg % of height
    "child": (520, 600, 44, 22), "teen": (660, 720, 38, 25),
    "adult": (740, 810, 36, 25), "elder": (700, 770, 37, 24),
}
BUILDS = {"slim": 78, "average": 92, "stocky": 110, "heavy": 128}  # torso width % of head width
HAIR = ("none", "topknot", "long", "wild", "braids", "bun", "mohawk", "ponytail", "twintails", "short")
TOPS = ("none", "tunic", "vest", "apron", "robe", "dress", "armor_light", "armor_heavy", "wrap", "cloak", "fur_mantle", "crop")
BOTTOMS = ("none", "trousers", "shorts", "skirt", "kilt")
HEADWEAR = ("none", "hood", "bandana", "goggles", "helm", "feather_crown", "chef_hat", "horns", "flower_crown",
            "headscarf", "cap", "circlet")
HELD = ("none", "hammer", "staff", "book", "bow", "basket", "spear", "dagger", "lute", "lantern", "ladle", "brush",
        "sword", "wrench", "mug", "teddy", "scroll", "orb", "map", "bag", "shield", "whip", "flask", "axe")
BACK = ("none", "backpack", "quiver", "cape", "big_pack", "fur")
ACCESSORIES = ("beard", "necklace", "earrings", "glasses", "goggles", "scarf", "pauldrons", "belt", "pouches",
               "bracers", "tusks", "fins", "tattoo")
EXPRESSIONS = ("neutral", "happy", "curious", "confident", "thoughtful", "annoyed", "angry", "surprised", "playful")
FIXED_MATERIALS = ("skin", "leather", "wood", "metal", "brass", "paper", "fur", "glow", "arcane", "gem",
                   "eye_white", "iris", "mouth", "teeth")


# ---------------------------------------------------------------- integer shapes
class Shape:
    __slots__ = ("kind", "a", "mat", "z", "feat", "bias", "snap", "bbox")

    def __init__(self, kind, a, mat, z, feat, bias=0, snap=False):
        self.kind, self.a, self.mat, self.z, self.feat, self.bias, self.snap = kind, a, mat, z, feat, bias, snap
        self.bbox = None


def E(cx, cy, rx, ry, mat, z, feat, **k):
    return Shape("E", [cx, cy, rx, ry], mat, z, feat, **k)


def R(x0, y0, x1, y1, rad, mat, z, feat, **k):
    return Shape("R", [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), rad], mat, z, feat, **k)


def C(x0, y0, x1, y1, r, mat, z, feat, **k):
    return Shape("C", [x0, y0, x1, y1, r], mat, z, feat, **k)


def T(x0, y0, x1, y1, x2, y2, mat, z, feat, **k):
    return Shape("T", [x0, y0, x1, y1, x2, y2], mat, z, feat, **k)


def A(cx, cy, rx, ry, th, half, mat, z, feat, **k):
    """Ring segment: between two ellipses; half = 1 lower, -1 upper, 0 full."""
    return Shape("A", [cx, cy, rx, ry, th, half], mat, z, feat, **k)


def _snap(s: Shape, halfpx: int) -> list:
    a = list(s.a)
    if not s.snap:
        return a
    if s.kind == "E":
        a[2], a[3] = max(a[2], halfpx), max(a[3], halfpx)
    elif s.kind == "C":
        a[4] = max(a[4], halfpx)
    elif s.kind == "R":
        if a[2] - a[0] < 2 * halfpx:
            m = (a[0] + a[2]) // 2
            a[0], a[2] = m - halfpx, m + halfpx
        if a[3] - a[1] < 2 * halfpx:
            m = (a[1] + a[3]) // 2
            a[1], a[3] = m - halfpx, m + halfpx
    elif s.kind == "A":
        a[4] = max(a[4], 2 * halfpx)
    elif s.kind == "T":
        a = a + [halfpx]
    return a


def _bbox(kind, a):
    if kind == "E":
        return a[0] - a[2], a[1] - a[3], a[0] + a[2], a[1] + a[3]
    if kind == "R":
        return a[0], a[1], a[2], a[3]
    if kind == "C":
        return min(a[0], a[2]) - a[4], min(a[1], a[3]) - a[4], max(a[0], a[2]) + a[4], max(a[1], a[3]) + a[4]
    if kind == "T":
        xs, ys = a[0:6:2], a[1:6:2]
        pad = a[6] if len(a) == 7 else 0
        return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    return a[0] - a[2], a[1] - a[3], a[0] + a[2], a[1] + a[3]


def _inside(kind, a, u, v) -> bool:
    if kind == "E":
        dx, dy, rx, ry = u - a[0], v - a[1], a[2], a[3]
        if rx <= 0 or ry <= 0:
            return False
        return dx * dx * ry * ry + dy * dy * rx * rx <= rx * rx * ry * ry
    if kind == "R":
        x0, y0, x1, y1, r = a
        if u < x0 or u > x1 or v < y0 or v > y1:
            return False
        r = min(r, (x1 - x0) // 2, (y1 - y0) // 2)
        dx = max(x0 + r - u, 0, u - (x1 - r))
        dy = max(y0 + r - v, 0, v - (y1 - r))
        return dx * dx + dy * dy <= r * r
    if kind == "C":
        x0, y0, x1, y1, r = a
        dx, dy = x1 - x0, y1 - y0
        px, py = u - x0, v - y0
        len2 = dx * dx + dy * dy
        dot = px * dx + py * dy
        if len2 == 0 or dot <= 0:
            return px * px + py * py <= r * r
        if dot >= len2:
            qx, qy = u - x1, v - y1
            return qx * qx + qy * qy <= r * r
        return (px * px + py * py) * len2 - dot * dot <= r * r * len2
    if kind == "T":
        x0, y0, x1, y1, x2, y2 = a[:6]
        if len(a) == 7 and _inside("C", [(x0 + x1) // 2, (y0 + y1) // 2, x2, y2, a[6]], u, v):
            return True
        d0 = (x1 - x0) * (v - y0) - (y1 - y0) * (u - x0)
        d1 = (x2 - x1) * (v - y1) - (y2 - y1) * (u - x1)
        d2 = (x0 - x2) * (v - y2) - (y0 - y2) * (u - x2)
        return (d0 >= 0 and d1 >= 0 and d2 >= 0) or (d0 <= 0 and d1 <= 0 and d2 <= 0)
    cx, cy, rx, ry, th, half = a
    if half == 1 and v < cy or half == -1 and v > cy:
        return False
    dx, dy = u - cx, v - cy
    if rx <= 0 or ry <= 0:
        return False
    if dx * dx * ry * ry + dy * dy * rx * rx > rx * rx * ry * ry:
        return False
    irx, iry = rx - th, ry - th
    if irx <= 0 or iry <= 0:
        return True
    return dx * dx * iry * iry + dy * dy * irx * irx > irx * irx * iry * iry


def isqrt(n: int) -> int:
    if n <= 0:
        return 0
    r = int(n ** 0.5)  # refined below so the result is exact in every language
    while r * r > n:
        r -= 1
    while (r + 1) * (r + 1) <= n:
        r += 1
    return r


# ---------------------------------------------------------------- genome
def _pick(rng, options, default="none"):
    if not options:
        return default
    return options[rng.below(len(options))]


def _rng_range(rng, pair):
    lo, hi = pair
    return lo + rng.below(hi - lo + 1) if hi > lo else lo


def genome(data: dict, S: Streams) -> dict:
    """Everything the character IS. Tier-independent. Each concern owns a stream."""
    sp = data.get("species", {})
    role = data.get("role", {})
    b = S.rng("g/body")
    age = _pick(b, role.get("age", ["adult"]), "adult")
    h_lo, h_hi, head_pct, leg_pct = AGES[age]
    g = {"age": age}
    g["height"] = _rng_range(b, (h_lo, h_hi))
    g["head_pct"] = head_pct + _rng_range(b, tuple(sp.get("head_adj", [-2, 2])))
    g["head_w_pct"] = _rng_range(b, tuple(sp.get("head_w", [92, 104])))
    g["build"] = _pick(b, role.get("build", sp.get("build", ["average"])), "average")
    g["ear_len"] = _rng_range(b, tuple(sp.get("ear_len", [60, 100])))
    g["ear_lift"] = _rng_range(b, tuple(sp.get("ear_lift", [-15, 25])))
    g["ear_w"] = _rng_range(b, tuple(sp.get("ear_w", [26, 34])))
    g["nose"] = _rng_range(b, tuple(sp.get("nose", [90, 130])))
    g["eye"] = _rng_range(b, tuple(sp.get("eye", [100, 120])))
    g["leg_pct"] = leg_pct
    g["hunch"] = 1 if age == "elder" else 0
    stature = sp.get("stature", None)
    if stature is not None:  # other folk (dwarves, elves): drawn only when a species sets it, so no existing stream moves
        g["height"] = min(1000, g["height"] * _rng_range(b, tuple(stature)) // 100)
    f = S.rng("g/face")
    g["expression"] = _pick(f, role.get("expression", ["neutral"]), "neutral")
    g["iris"] = _pick(f, sp.get("iris", ["amber"]), "amber")
    h = S.rng("g/hair")
    g["hair"] = _pick(h, role.get("hair", sp.get("hair", ["short"])), "none")
    g["hair_color"] = _pick(h, role.get("hair_color", sp.get("hair_color", ["black"])), "black")
    o = S.rng("g/outfit")
    g["top"] = _pick(o, role.get("top", ["tunic"]))
    g["bottom"] = _pick(o, role.get("bottom", ["trousers"]))
    g["cloth_a"] = _pick(o, role.get("cloth_a", ["red"]), "red")
    g["cloth_b"] = _pick(o, role.get("cloth_b", ["leather"]), "leather")
    hw = S.rng("g/headwear")
    g["headwear"] = _pick(hw, role.get("headwear", ["none"]))
    it = S.rng("g/items")
    g["held"] = _pick(it, role.get("held", ["none"]))
    g["offhand"] = _pick(it, role.get("offhand", ["none"]))
    g["back"] = _pick(it, role.get("back", ["none"]))
    items = data.get("items", {})
    for slot in ("held", "offhand"):  # items written as data travel with the genome
        if g[slot] in items:
            g[slot + "_spec"] = items[g[slot]]["shapes"]
    ac = S.rng("g/accessories")
    acc = []
    for entry in role.get("accessories", []) + sp.get("accessories", []):
        if ac.chance(entry.get("chance", 100)):
            acc.append(entry["item"])
    g["accessories"] = sorted(set(acc))
    team = data.get("team")
    if team:  # clan colours are applied after the character is decided (typefile.with_team)
        g["cloth_a"], g["cloth_b"], g["team"] = team["a"], team["b"], team["name"]
    return g


# ---------------------------------------------------------------- geometry
def build_shapes(g: dict, px: int, pose: dict, style_px: int | None = None) -> list[Shape]:
    """Shapes in design units for one pose. `px` = design units per pixel at the
    target tier, used only for pixel-true rules (leg gap, 1-pixel animation)."""
    H = g["height"]
    top = GROUND - H
    tier = D // (style_px or px)
    head_h = H * (g["head_pct"] + TIER_HEAD.get(tier, 0)) // 100
    head_w = head_h * g["head_w_pct"] // 100
    bob = pose.get("bob", 0) * px
    hunch = g["hunch"] * px
    head_cy = top + head_h // 2 + bob + hunch
    leg_len = H * g["leg_pct"] // 100
    hip_y = GROUND - leg_len
    neck_y = top + head_h - head_h // 10 + bob
    sh_y = neck_y + head_h // 10
    tw = head_w * BUILDS[g["build"]] // 100
    torso_h = hip_y - sh_y
    s: list[Shape] = []
    acc = set(g["accessories"])
    top_kind, bottom = g["top"], g["bottom"]
    long_robe = top_kind in ("robe",)

    # --- back layer
    back = g["back"]
    if back == "cape" or top_kind == "cloak":
        s.append(T(CX - tw * 55 // 100, sh_y, CX + tw * 55 // 100, sh_y, CX + tw * 80 // 100, hip_y + leg_len * 70 // 100, "cloth_a", 2, "back.large"))
        s.append(T(CX - tw * 55 // 100, sh_y, CX - tw * 80 // 100, hip_y + leg_len * 70 // 100, CX + tw * 80 // 100, hip_y + leg_len * 70 // 100, "cloth_a", 2, "back.large"))
    if back == "backpack":
        s.append(R(CX - tw * 72 // 100, sh_y - head_h // 8 + bob, CX + tw * 72 // 100, hip_y - torso_h // 10, tw // 8, "leather", 2, "back.large"))
        s.append(R(CX - tw * 30 // 100, sh_y - head_h * 30 // 100 + bob, CX + tw * 30 // 100, sh_y - head_h // 10 + bob, tw // 10, "cloth_b", 3, "back"))
    if back == "big_pack":
        s.append(R(CX - tw * 70 // 100, sh_y - head_h * 55 // 100 + bob, CX + tw * 70 // 100, hip_y, tw // 6, "leather", 2, "back.large"))
        s.append(E(CX - tw * 40 // 100, sh_y - head_h * 55 // 100 + bob, tw * 20 // 100, tw * 16 // 100, "brass", 3, "back"))
        s.append(E(CX + tw * 45 // 100, sh_y - head_h * 50 // 100 + bob, tw * 16 // 100, tw * 20 // 100, "wood", 3, "back"))
    if back == "quiver":
        s.append(C(CX + tw * 30 // 100, sh_y - head_h * 30 // 100 + bob, CX - tw * 25 // 100, hip_y - torso_h // 6, tw * 13 // 100, "leather", 2, "back.large"))
        for i in range(3):
            x = CX + tw * (22 + i * 9) // 100
            s.append(T(x - tw * 5 // 100, sh_y - head_h * 30 // 100 + bob, x + tw * 5 // 100, sh_y - head_h * 30 // 100 + bob, x, sh_y - head_h * 48 // 100 + bob, "metal", 3, "back"))
    if back == "fur":
        s.append(E(CX, sh_y + torso_h // 6, tw * 70 // 100, torso_h * 45 // 100, "fur", 3, "back.large"))
    if g["hair"] == "long":
        s.append(E(CX, head_cy + head_h * 25 // 100, head_w * 52 // 100, head_h * 62 // 100, "hair", 4, "hair"))
    if g["hair"] == "ponytail":
        s.append(C(CX + head_w * 30 // 100, head_cy - head_h * 20 // 100, CX + head_w * 50 // 100, head_cy + head_h * 55 // 100, head_w * 12 // 100, "hair", 4, "hair"))

    # --- legs (the gap between them never closes)
    leg_r = max(tw * 15 // 100, px // 2)
    lx = max(tw * 27 // 100, leg_r + px // 2 + px)
    foot_h = max(leg_r, px)
    lift_l, lift_r = pose.get("lift_l", 0) * px, pose.get("lift_r", 0) * px
    for side, lift in ((-1, lift_l), (1, lift_r)):
        fx = CX + side * lx
        s.append(C(CX + side * lx, hip_y - leg_r // 2, fx, GROUND - foot_h - lift, leg_r, "skin", 10, "legs"))
        # below 32 px the feet are drawn in front of everything, even a role's
        # signature item: a held spear or
        # shield covering both feet makes an 8 px character float
        s.append(E(fx + side * leg_r // 3, GROUND - foot_h // 2 - lift, leg_r * 14 // 10, foot_h * 6 // 10 + 1, "leather",
                   12 if tier >= 32 else 200, "feet"))
    if bottom == "trousers" or bottom == "shorts":
        knee = hip_y + (leg_len * 45 // 100 if bottom == "trousers" else leg_len * 30 // 100)
        for side, lift in ((-1, lift_l), (1, lift_r)):
            end_y = GROUND - foot_h * 2 - lift if bottom == "trousers" else knee
            s.append(C(CX + side * lx, hip_y - leg_r // 2, CX + side * lx, end_y, leg_r * 12 // 10, "cloth_b", 14, "bottom"))
        s.append(R(CX - lx - leg_r, hip_y - leg_r, CX + lx + leg_r, hip_y + leg_r // 2, leg_r // 2, "cloth_b", 14, "bottom"))
    if bottom in ("skirt", "kilt"):
        hem = hip_y + leg_len * (55 if bottom == "skirt" else 35) // 100
        mat = "cloth_b" if bottom == "skirt" else "leather"
        s.append(T(CX - tw * 45 // 100, hip_y - leg_r, CX + tw * 45 // 100, hip_y - leg_r, CX + tw * 62 // 100, hem, mat, 15, "bottom"))
        s.append(T(CX - tw * 45 // 100, hip_y - leg_r, CX - tw * 62 // 100, hem, CX + tw * 62 // 100, hem, mat, 15, "bottom"))

    # --- torso and top
    s.append(R(CX - tw // 2, sh_y + bob, CX + tw // 2, hip_y + leg_r, tw * 30 // 100, "skin", 20, "torso"))
    ta = "cloth_a"
    if top_kind in ("tunic", "crop", "wrap", "cloak"):
        hem = hip_y + (leg_len * 30 // 100 if top_kind == "tunic" else -torso_h // 4 if top_kind == "crop" else leg_r)
        s.append(R(CX - tw * 54 // 100, sh_y + bob - px, CX + tw * 54 // 100, hem, tw * 28 // 100, ta, 22, "top"))
        if top_kind == "wrap":
            s.append(C(CX - tw * 45 // 100, sh_y + bob, CX + tw * 40 // 100, hip_y - torso_h // 6, tw * 10 // 100, "cloth_b", 23, "pattern"))
    elif top_kind == "vest":
        s.append(R(CX - tw * 54 // 100, sh_y + bob - px, CX - tw * 10 // 100, hip_y + leg_r, tw * 20 // 100, ta, 22, "top"))
        s.append(R(CX + tw * 10 // 100, sh_y + bob - px, CX + tw * 54 // 100, hip_y + leg_r, tw * 20 // 100, ta, 22, "top"))
        s.append(R(CX - tw * 12 // 100, sh_y + bob, CX + tw * 12 // 100, hip_y, tw // 20, "cloth_b", 21, "top"))
    elif top_kind in ("robe", "dress"):
        hem = GROUND - foot_h if top_kind == "robe" else hip_y + leg_len * 55 // 100
        wide = tw * (70 if top_kind == "robe" else 78) // 100
        s.append(R(CX - tw * 54 // 100, sh_y + bob - px, CX + tw * 54 // 100, hip_y, tw * 28 // 100, ta, 22, "top"))
        s.append(T(CX - tw * 50 // 100, hip_y - torso_h // 4, CX + tw * 50 // 100, hip_y - torso_h // 4, CX + wide, hem, ta, 23, "top"))
        s.append(T(CX - tw * 50 // 100, hip_y - torso_h // 4, CX - wide, hem, CX + wide, hem, ta, 23, "top"))
        s.append(C(CX, sh_y + bob + torso_h // 5, CX, hem - px, max(tw * 5 // 100, 1), "cloth_b", 24, "pattern"))
    elif top_kind == "apron":
        s.append(R(CX - tw * 54 // 100, sh_y + bob - px, CX + tw * 54 // 100, hip_y + leg_r, tw * 28 // 100, "cloth_b", 22, "top"))
        s.append(R(CX - tw * 40 // 100, sh_y + bob + torso_h // 4, CX + tw * 40 // 100, hip_y + leg_len * 55 // 100, tw // 10, "leather", 25, "top"))
    elif top_kind == "armor_light":
        s.append(R(CX - tw * 55 // 100, sh_y + bob - px, CX + tw * 55 // 100, hip_y + leg_r, tw * 25 // 100, "leather", 22, "top"))
        s.append(C(CX - tw * 45 // 100, sh_y + bob, CX + tw * 45 // 100, hip_y - torso_h // 8, max(tw * 7 // 100, 1), "cloth_a", 23, "straps"))
    elif top_kind == "armor_heavy":
        s.append(R(CX - tw * 58 // 100, sh_y + bob - px, CX + tw * 58 // 100, hip_y + leg_len * 25 // 100, tw * 22 // 100, "metal", 22, "top"))
        s.append(R(CX - tw * 30 // 100, sh_y + bob + torso_h // 5, CX + tw * 30 // 100, hip_y - torso_h // 8, tw // 10, "cloth_a", 23, "pattern"))
    elif top_kind == "fur_mantle":
        s.append(R(CX - tw * 54 // 100, sh_y + bob - px, CX + tw * 54 // 100, hip_y + leg_r, tw * 28 // 100, ta, 22, "top"))
    if top_kind == "fur_mantle" or "fur" == back:
        s.append(E(CX, sh_y + bob + torso_h // 10, tw * 68 // 100, torso_h * 28 // 100, "fur", 26, "top"))
    if back in ("backpack", "big_pack", "quiver"):
        for side in (-1, 1):
            s.append(C(CX + side * tw * 30 // 100, sh_y + bob, CX + side * tw * 26 // 100, hip_y - torso_h // 4, max(px // 2, tw // 16), "leather", 27, "straps", snap=True))
    if "belt" in acc or top_kind in ("tunic", "robe", "armor_light", "apron"):
        s.append(R(CX - tw * 55 // 100, hip_y - torso_h // 8, CX + tw * 55 // 100, hip_y - torso_h // 8 + max(torso_h // 9, px), px // 2, "leather", 27, "belt", snap=True))
        s.append(R(CX - tw * 9 // 100, hip_y - torso_h // 8 - px // 2, CX + tw * 9 // 100, hip_y - torso_h // 8 + max(torso_h // 9, px) + px // 2, px // 2, "brass", 28, "buckle"))
    if "pouches" in acc:
        for side in (-1, 1):
            s.append(R(CX + side * tw * 35 // 100 - tw // 10, hip_y - torso_h // 10, CX + side * tw * 35 // 100 + tw // 10, hip_y + torso_h // 10, tw // 20, "leather", 29, "pouches"))
    if "necklace" in acc:
        s.append(A(CX, sh_y + bob, tw * 32 // 100, torso_h * 30 // 100, max(px, torso_h // 25), 1, "brass", 28, "necklace"))
        s.append(E(CX, sh_y + bob + torso_h * 30 // 100, tw * 6 // 100, tw * 6 // 100, "gem", 29, "necklace"))
    if "scarf" in acc:
        s.append(R(CX - tw * 45 // 100, sh_y + bob - head_h // 12, CX + tw * 45 // 100, sh_y + bob + head_h // 12, tw // 10, "cloth_b", 29, "scarf"))
        s.append(C(CX + tw * 20 // 100, sh_y + bob, CX + tw * 30 // 100, sh_y + bob + torso_h * 45 // 100, tw * 8 // 100, "cloth_b", 29, "scarf"))
    if "pauldrons" in acc:
        for side in (-1, 1):
            s.append(E(CX + side * tw * 50 // 100, sh_y + bob + head_h // 20, tw * 28 // 100, tw * 20 // 100, "metal", 36, "pauldrons"))
    if "tattoo" in acc:
        for i in range(2):
            y = sh_y + bob + torso_h * (30 + i * 18) // 100
            s.append(C(CX - tw * 42 // 100, y, CX - tw * 20 // 100, y + px, max(px // 2, 1), "arcane", 24, "pattern"))

    # --- arms and hands
    arm_r = max(tw * 12 // 100, px // 2)
    swing = pose.get("swing", 0) * px
    hands = {}
    for side in (-1, 1):
        sx, sy = CX + side * (tw // 2 - arm_r // 2), sh_y + bob + arm_r
        hx = CX + side * (tw // 2 + tw * 14 // 100)
        hy = hip_y + arm_r + side * swing + bob
        s.append(C(sx, sy, hx, hy, arm_r, "skin", 30, "arms"))
        if top_kind in ("tunic", "robe", "dress", "fur_mantle", "armor_heavy", "cloak", "wrap"):
            mat = "metal" if top_kind == "armor_heavy" else ta
            s.append(C(sx, sy, (sx + hx) // 2, (sy + hy) // 2, arm_r * 12 // 10, mat, 31, "sleeves"))
        if "bracers" in acc:
            s.append(C((sx + 2 * hx) // 3, (sy + 2 * hy) // 3, hx, hy - arm_r, arm_r * 11 // 10, "leather", 31, "bracers"))
        s.append(E(hx, hy, arm_r * 13 // 10, arm_r * 13 // 10, "skin", 33, "hands"))
        hands[side] = (hx, hy)
    if g.get("held_spec", None) is not None:
        _held_data(s, g["held_spec"], hands[-1], -1, head_h, px)
    else:
        _held(s, g["held"], hands[-1], -1, tw, head_h, px)
    if g.get("offhand_spec", None) is not None:
        _held_data(s, g["offhand_spec"], hands[1], 1, head_h, px)
    else:
        _held(s, g["offhand"], hands[1], 1, tw, head_h, px)

    # --- head
    ear_len = min(head_w * g["ear_len"] // 100, 496 - head_w // 2)  # ear tips stay on the canvas
    ear_w = head_h * g["ear_w"] // 100
    for side in (-1, 1):
        bx = CX + side * head_w * 38 // 100
        tip = (CX + side * (head_w // 2 + ear_len), head_cy - head_h * g["ear_lift"] // 100)
        s.append(T(bx, head_cy - ear_w * 6 // 10, bx, head_cy + ear_w * 4 // 10, tip[0], tip[1], "skin", 40, "ears", snap=True))
        s.append(T(bx + side * head_w // 20, head_cy - ear_w * 3 // 10, bx + side * head_w // 20, head_cy + ear_w // 5,
                   CX + side * (head_w // 2 + ear_len * 7 // 10), tip[1] + (head_cy - tip[1]) // 5, "skin", 41, "ear_inner", bias=-1))
        if "earrings" in acc:
            s.append(A(bx + side * ear_len // 3, head_cy + ear_w * 3 // 10, head_w // 14, head_w // 14, max(px, head_w // 40), 0, "brass", 42, "earrings"))
        if "fins" in acc:
            s.append(T(bx + side * ear_len // 4, head_cy - ear_w, bx + side * ear_len, head_cy - ear_w * 14 // 10, bx + side * ear_len * 7 // 10, head_cy - ear_w // 5, "arcane", 39, "fins"))
    s.append(E(CX, head_cy, head_w // 2, head_h // 2, "skin", 44, "head"))
    s.append(E(CX, head_cy + head_h // 6, head_w * 40 // 100, head_h * 40 // 100, "skin", 44, "head"))
    _face(s, g, head_cy, head_w, head_h, px, pose, style_px or px)
    _hair(s, g["hair"], head_cy, head_w, head_h, px)
    _headwear(s, g["headwear"], head_cy, head_w, head_h, px)
    if "glasses" in acc:
        for side in (-1, 1):
            s.append(A(CX + side * head_w * 20 // 100, head_cy + head_h * 4 // 100, head_w * 14 // 100, head_h * 12 // 100, max(px, head_w // 40), 0, "brass", 56, "glasses", snap=True))
    if "goggles" in acc and g["headwear"] != "goggles":
        _goggles(s, head_cy - head_h * 30 // 100, head_w, head_h, px, 57)
    for sh in s:
        sh.a = [int(v) for v in sh.a]
    return s


def _goggles(s, y, head_w, head_h, px, z):
    s.append(R(CX - head_w * 50 // 100, y - head_h // 22, CX + head_w * 50 // 100, y + head_h // 22, px // 2, "leather", z, "goggles", snap=True))
    for side in (-1, 1):
        s.append(E(CX + side * head_w * 20 // 100, y, head_w * 14 // 100, head_h * 11 // 100, "brass", z + 1, "goggles"))
        s.append(E(CX + side * head_w * 20 // 100, y, head_w * 9 // 100, head_h * 7 // 100, "gem", z + 2, "highlights"))


def _face(s, g, cy, hw, hh, px, pose, style_px):
    ey = cy + hh * 4 // 100
    boost = 100 + TIER_EYE.get(D // style_px, 0)
    erx, ery = hw * 10 * g["eye"] * boost // 1000000, hh * 9 * g["eye"] * boost // 1000000
    # the two eyes never merge: at least one clear pixel between them
    ex_off = max(hw * 21 // 100, max(erx, px // 2) + px)
    expr = g["expression"]
    blink = pose.get("blink", 0)
    for side in (-1, 1):
        ex = CX + side * ex_off
        wink = expr == "playful" and side == 1
        if blink or wink:
            s.append(C(ex - erx, ey, ex + erx, ey, max(px // 2, hh // 60), "mouth", 50, "eyes", snap=True))
            continue
        s.append(E(ex, ey, erx, ery, "iris", 50, "eyes", snap=True))
        s.append(E(ex, ey, erx, ery, "eye_white", 51, "eye_whites"))
        s.append(E(ex + side * erx // 5, ey, erx * 60 // 100, ery * 70 // 100, "iris", 52, "eye_whites"))
        s.append(E(ex + side * erx // 5, ey, erx * 28 // 100, ery * 36 // 100, "mouth", 53, "pupils"))
        s.append(E(ex - erx // 3, ey - ery // 3, erx // 5 + 1, ery // 5 + 1, "eye_white", 54, "highlights"))
        # brows: inner end (towards the nose) moves with the expression
        tilt = {"angry": 3, "annoyed": 2, "surprised": -2, "thoughtful": 1 if side == 1 else 0}.get(expr, 0)
        lift = hh * 5 // 100 if expr == "surprised" or (expr == "curious" and side == -1) else 0
        by = ey - ery - hh * 7 // 100 - lift
        inner, outer = ex - side * erx * 12 // 10, ex + side * erx * 12 // 10
        s.append(C(inner, by + tilt * hh // 60, outer, by, max(px // 2, hh // 50), "hair", 55, "brows"))
    # nose (goblins: long)
    s.append(E(CX, cy + hh * 18 // 100, hw * 9 * g["nose"] // 10000, hh * 15 * g["nose"] // 10000, "skin", 52, "nose", bias=-1))
    s.append(E(CX - hw * 2 // 100, cy + hh * 15 // 100, hw * 4 * g["nose"] // 10000, hh * 7 * g["nose"] // 10000, "skin", 53, "highlights", bias=1))
    my, mw = cy + hh * 33 // 100, hw * 22 // 100
    th = max(px, hh // 40)
    if expr in ("happy", "playful"):
        s.append(A(CX, my - hh * 6 // 100, mw, hh * 10 // 100, th, 1, "mouth", 53, "mouth", snap=True))
        if expr == "playful":
            s.append(E(CX + mw // 3, my + hh * 5 // 100, mw // 4, hh * 5 // 100, "mouth", 54, "tongue", bias=2))
    elif expr == "angry":
        s.append(A(CX, my + hh * 7 // 100, mw, hh * 9 // 100, th, -1, "mouth", 53, "mouth", snap=True))
        for side in (-1, 1):
            s.append(T(CX + side * mw * 6 // 10, my - th, CX + side * mw * 3 // 10, my - th, CX + side * mw * 45 // 100, my - hh * 9 // 100, "teeth", 54, "tusks"))
    elif expr == "surprised" or expr == "curious":
        r = mw * (45 if expr == "surprised" else 28) // 100
        s.append(E(CX, my, r, r * 12 // 10, "mouth", 53, "mouth", snap=True))
    elif expr == "confident":
        s.append(A(CX + mw // 3, my - hh * 5 // 100, mw * 7 // 10, hh * 8 // 100, th, 1, "mouth", 53, "mouth", snap=True))
        s.append(T(CX - mw * 5 // 10, my, CX - mw * 3 // 10, my, CX - mw * 4 // 10, my - hh * 9 // 100, "teeth", 54, "tusks"))
    else:
        off = mw // 4 if expr == "thoughtful" else 0
        s.append(C(CX - mw * 7 // 10 + off, my, CX + mw * 7 // 10 + off, my + (hh // 60 if expr == "annoyed" else 0), th // 2 + 1, "mouth", 53, "mouth", snap=True))
    if "tusks" in g["accessories"] and expr != "angry":
        for side in (-1, 1):
            s.append(T(CX + side * mw * 6 // 10, my + th, CX + side * mw * 3 // 10, my + th, CX + side * mw * 45 // 100, my - hh * 8 // 100, "teeth", 54, "tusks"))
    if "beard" in g["accessories"]:
        s.append(T(CX - hw * 34 // 100, cy + hh * 26 // 100, CX + hw * 34 // 100, cy + hh * 26 // 100, CX, cy + hh * 95 // 100, "hair", 56, "beard"))
        s.append(E(CX, cy + hh * 45 // 100, hw * 32 // 100, hh * 22 // 100, "hair", 56, "beard"))
        s.append(C(CX - hw * 25 // 100, cy + hh * 28 // 100, CX + hw * 25 // 100, cy + hh * 28 // 100, hh // 18, "hair", 57, "beard"))


def _hair(s, style, cy, hw, hh, px):
    top = cy - hh // 2
    if style == "none":
        return
    if style in ("short", "wild", "braids", "twintails", "long", "ponytail", "bun", "topknot"):
        s.append(A(CX, cy - hh // 10, hw * 51 // 100, hh * 44 // 100, hh * 16 // 100, -1, "hair", 58, "hair"))
    if style == "topknot":
        s.append(E(CX, top - hh // 10, hw * 16 // 100, hh * 16 // 100, "hair", 58, "hair", snap=True))
    if style == "bun":
        s.append(E(CX, top + hh // 20, hw * 22 // 100, hh * 18 // 100, "hair", 57, "hair"))
    if style == "mohawk":
        s.append(E(CX, top + hh // 20, hw * 10 // 100, hh * 30 // 100, "hair", 58, "hair", snap=True))
    if style == "wild":
        for i in range(-2, 3):
            s.append(T(CX + i * hw * 18 // 100 - hw // 10, top + hh // 6, CX + i * hw * 18 // 100 + hw // 10, top + hh // 6,
                       CX + i * hw * 24 // 100, top - hh // 6 - abs(i) * hh // 30, "hair", 59, "hair"))
    if style == "braids" or style == "twintails":
        for side in (-1, 1):
            if style == "braids":
                s.append(C(CX + side * hw * 45 // 100, cy, CX + side * hw * 50 // 100, cy + hh * 70 // 100, hw * 8 // 100, "hair", 59, "hair", snap=True))
            else:
                s.append(E(CX + side * hw * 55 // 100, cy - hh * 10 // 100, hw * 16 // 100, hh * 30 // 100, "hair", 43, "hair"))


def _headwear(s, kind, cy, hw, hh, px):
    top = cy - hh // 2
    z = 60
    if kind == "hood":
        s.append(A(CX, cy + hh // 10, hw * 58 // 100, hh * 62 // 100, hh * 20 // 100, -1, "cloth_a", z, "headwear.large"))
        s.append(T(CX - hw // 5, top - hh // 20, CX + hw // 5, top - hh // 20, CX + hw // 4, top - hh * 30 // 100, "cloth_a", z, "headwear"))
    elif kind == "bandana":
        s.append(R(CX - hw * 50 // 100, cy - hh * 22 // 100, CX + hw * 50 // 100, cy - hh * 12 // 100, px // 2, "cloth_b", z, "headwear", snap=True))
        s.append(T(CX + hw * 45 // 100, cy - hh * 18 // 100, CX + hw * 70 // 100, cy - hh * 5 // 100, CX + hw * 62 // 100, cy - hh * 30 // 100, "cloth_b", z, "headwear"))
    elif kind == "goggles":
        _goggles(s, cy - hh * 30 // 100, hw, hh, px, z)
    elif kind == "helm":
        s.append(A(CX, cy - hh // 20, hw * 54 // 100, hh * 50 // 100, hh * 24 // 100, -1, "metal", z, "headwear.large"))
        s.append(R(CX - hw // 25, cy - hh // 5, CX + hw // 25, cy + hh * 12 // 100, px // 2, "metal", z + 1, "headwear", snap=True))
    elif kind == "feather_crown":
        s.append(R(CX - hw * 46 // 100, cy - hh * 34 // 100, CX + hw * 46 // 100, cy - hh * 24 // 100, px // 2, "brass", z, "headwear", snap=True))
        for i in range(-2, 3):
            s.append(C(CX + i * hw * 17 // 100, cy - hh * 34 // 100, CX + i * hw * 26 // 100, top - hh * 42 // 100 + abs(i) * hh // 10,
                       hw * 5 // 100, "cloth_a" if i % 2 else "fur", z - 1, "headwear.large", snap=True))
    elif kind == "chef_hat":
        s.append(E(CX, top - hh // 8, hw * 40 // 100, hh * 30 // 100, "paper", z, "headwear.large"))
        s.append(R(CX - hw * 36 // 100, top - hh // 20, CX + hw * 36 // 100, top + hh // 10, hw // 20, "paper", z + 1, "headwear"))
    elif kind == "horns":
        for side in (-1, 1):
            s.append(C(CX + side * hw * 25 // 100, top + hh // 8, CX + side * hw * 55 // 100, top - hh * 25 // 100, hw * 7 // 100, "fur", z, "headwear.large", snap=True))
            s.append(C(CX + side * hw * 55 // 100, top - hh * 25 // 100, CX + side * hw * 45 // 100, top - hh * 45 // 100, hw * 5 // 100, "fur", z, "headwear.large", snap=True))
        s.append(R(CX - hw * 46 // 100, cy - hh * 34 // 100, CX + hw * 46 // 100, cy - hh * 24 // 100, px // 2, "leather", z + 1, "headwear", snap=True))
    elif kind == "flower_crown":
        s.append(A(CX, cy - hh // 10, hw * 50 // 100, hh * 32 // 100, max(px, hh // 20), -1, "wood", z, "headwear", snap=True))
        for i in range(-2, 3):
            s.append(E(CX + i * hw * 20 // 100, cy - hh * 35 // 100 - (2 - abs(i)) * hh // 40, hw * 6 // 100, hw * 6 // 100,
                       "cloth_a" if i % 2 else "glow", z + 1, "flowers"))
    elif kind == "headscarf":
        s.append(A(CX, cy, hw * 54 // 100, hh * 55 // 100, hh * 20 // 100, -1, "cloth_b", z, "headwear.large"))
        s.append(T(CX + hw * 40 // 100, cy - hh // 10, CX + hw * 62 // 100, cy + hh * 30 // 100, CX + hw * 30 // 100, cy + hh * 25 // 100, "cloth_b", z, "headwear"))
    elif kind == "cap":
        s.append(A(CX, cy - hh // 12, hw * 50 // 100, hh * 44 // 100, hh * 22 // 100, -1, "cloth_b", z, "headwear.large"))
    elif kind == "circlet":
        s.append(R(CX - hw * 48 // 100, cy - hh * 26 // 100, CX + hw * 48 // 100, cy - hh * 20 // 100, px // 2, "brass", z, "headwear", snap=True))
        s.append(E(CX, cy - hh * 23 // 100, hw * 6 // 100, hw * 6 // 100, "gem", z + 1, "headwear"))


def _held(s, kind, hand, side, tw, hh, px):
    hx, hy = hand
    z = 34
    if kind == "none":
        return
    L = hh * 13 // 10  # item scale follows head size, so children hold smaller things
    if kind == "hammer":
        s.append(C(hx, hy + L // 5, hx + side * L // 8, hy - L * 70 // 100, L // 16, "wood", z, "held.large", snap=True))
        s.append(R(hx + side * L // 8 - L // 5, hy - L * 85 // 100, hx + side * L // 8 + L // 5, hy - L * 62 // 100, L // 30, "metal", z + 1, "held.large"))
    elif kind in ("staff", "spear"):
        s.append(C(hx, hy + L * 60 // 100, hx, hy - L * 150 // 100, L // 18, "wood", z, "held.large", snap=True))
        if kind == "staff":
            s.append(E(hx, hy - L * 158 // 100, L // 7, L // 7, "arcane", z + 1, "held.large"))
            s.append(E(hx - L // 30, hy - L * 164 // 100, L // 20, L // 20, "glow", z + 2, "highlights"))
        else:
            s.append(T(hx - L // 10, hy - L * 145 // 100, hx + L // 10, hy - L * 145 // 100, hx, hy - L * 185 // 100, "metal", z + 1, "held.large", snap=True))
    elif kind == "book":
        s.append(R(hx - side * L * 5 // 100 - L // 4, hy - L // 3, hx - side * L * 5 // 100 + L // 4, hy + L // 20, L // 30, "leather", z + 1, "held"))
        s.append(R(hx - side * L * 5 // 100 - L // 5, hy - L * 29 // 100, hx - side * L * 5 // 100 + L // 5, hy + L // 60, L // 60, "paper", z + 2, "pattern"))
    elif kind == "bow":
        s.append(A(hx - side * L // 8, hy - L // 4, L // 3, L * 75 // 100, max(px, L // 18), 0, "wood", z, "held.large", snap=True))
        s.append(R(hx - side * L // 8 - L // 3 - L // 60, hy - L, hx - side * L // 8 - L // 3 + L // 60, hy + L // 2, 0, "paper", z - 1, "held"))
    elif kind == "basket":
        s.append(E(hx, hy + L // 10, L * 35 // 100, L * 25 // 100, "wood", z + 1, "held"))
        s.append(R(hx - L * 35 // 100, hy - L // 20, hx + L * 35 // 100, hy + L // 10, L // 20, "wood", z + 1, "held"))
        for i in range(-1, 2):
            s.append(E(hx + i * L // 7, hy - L // 12, L // 12, L // 12, "cloth_a" if i else "glow", z + 2, "flowers"))
    elif kind in ("dagger", "sword"):
        n = 60 if kind == "dagger" else 120
        s.append(T(hx - L // 18, hy - L // 12, hx + L // 18, hy - L // 12, hx + side * L // 20, hy - L * n // 100, "metal", z + 1, "held.large" if kind == "sword" else "held", snap=True))
        s.append(R(hx - L // 7, hy - L // 12, hx + L // 7, hy - L // 20, px // 2, "brass", z + 2, "held"))
    elif kind == "axe":
        s.append(C(hx, hy + L // 5, hx, hy - L * 90 // 100, L // 16, "wood", z, "held.large", snap=True))
        s.append(T(hx, hy - L * 95 // 100, hx, hy - L * 55 // 100, hx + side * L * 35 // 100, hy - L * 75 // 100, "metal", z + 1, "held.large"))
    elif kind == "lute":
        s.append(C(hx, hy, hx + side * L * 50 // 100, hy - L * 70 // 100, L // 16, "wood", z, "held"))
        s.append(E(hx - side * L // 10, hy + L // 10, L * 28 // 100, L * 32 // 100, "wood", z + 1, "held.large"))
        s.append(E(hx - side * L // 10, hy + L // 20, L // 12, L // 12, "leather", z + 2, "pattern"))
    elif kind == "lantern":
        s.append(C(hx, hy, hx, hy + L // 5, L // 40 + 1, "metal", z, "held"))
        s.append(R(hx - L // 7, hy + L // 5, hx + L // 7, hy + L // 2, L // 20, "brass", z + 1, "held"))
        s.append(E(hx, hy + L * 35 // 100, L // 12, L // 10, "glow", z + 2, "held"))
    elif kind in ("ladle", "brush", "wrench", "whip"):
        s.append(C(hx, hy + L // 6, hx + side * L // 5, hy - L * 65 // 100, L // 22, "wood" if kind != "wrench" else "metal", z, "held", snap=True))
        tipm = {"ladle": "metal", "brush": "cloth_a", "wrench": "metal", "whip": "leather"}[kind]
        s.append(E(hx + side * L // 5, hy - L * 70 // 100, L // 8, L // 10, tipm, z + 1, "held"))
    elif kind == "mug":
        s.append(R(hx - L // 7, hy - L // 5, hx + L // 7, hy + L // 8, L // 25, "wood", z + 1, "held"))
        s.append(E(hx, hy - L // 5, L // 7, L // 16, "paper", z + 2, "held"))
    elif kind == "teddy":
        s.append(E(hx, hy + L // 12, L // 6, L // 5, "fur", z + 1, "held"))
        s.append(E(hx, hy - L // 6, L // 7, L // 8, "fur", z + 1, "held"))
        for sd in (-1, 1):
            s.append(E(hx + sd * L // 10, hy - L // 4, L // 20, L // 20, "fur", z + 1, "held"))
    elif kind in ("scroll", "map"):
        s.append(R(hx - L // 4, hy - L // 6, hx + L // 4, hy + L // 20, L // 40, "paper", z + 1, "held"))
        s.append(C(hx - L // 4, hy - L // 6, hx - L // 4, hy + L // 20, L // 25, "wood", z + 2, "held"))
    elif kind == "orb":
        s.append(E(hx, hy - L // 6, L // 6, L // 6, "arcane", z + 1, "held.large"))
        s.append(E(hx - L // 20, hy - L // 5, L // 18, L // 18, "glow", z + 2, "highlights"))
    elif kind == "bag":
        s.append(E(hx, hy + L // 8, L // 5, L // 5, "leather", z + 1, "held"))
    elif kind == "flask":
        s.append(E(hx, hy, L // 8, L // 7, "gem", z + 1, "held"))
        s.append(R(hx - L // 30, hy - L // 4, hx + L // 30, hy - L // 9, 0, "paper", z + 1, "held", snap=True))
    elif kind == "shield":
        s.append(E(hx - side * L // 12, hy - L // 6, L * 36 // 100, L * 42 // 100, "wood", z + 1, "held.large"))
        s.append(A(hx - side * L // 12, hy - L // 6, L * 36 // 100, L * 42 // 100, max(px, L // 20), 0, "metal", z + 2, "held"))
        s.append(E(hx - side * L // 12, hy - L // 6, L // 12, L // 12, "brass", z + 3, "held"))


def _held_data(s, spec, hand, side, hh, px):
    """An item written as data: shapes in hundredths of the item scale L,
    relative to the hand, with x mirrored for the left hand. See the `items`
    table in docs/reference/type-files.md."""
    hx, hy = hand
    L = hh * 13 // 10
    for sh in spec:
        k = sh["shape"]
        a = sh["at"]
        z = 34 + sh.get("layer", 0)
        mat = sh["mat"]
        feat = sh.get("feat", "held")
        snap = sh.get("snap", False)
        if k == "E":
            s.append(E(hx + side * a[0] * L // 100, hy + a[1] * L // 100, a[2] * L // 100, a[3] * L // 100, mat, z, feat, snap=snap))
        elif k == "R":
            s.append(R(hx + side * a[0] * L // 100, hy + a[1] * L // 100, hx + side * a[2] * L // 100, hy + a[3] * L // 100, a[4] * L // 100, mat, z, feat, snap=snap))
        elif k == "C":
            s.append(C(hx + side * a[0] * L // 100, hy + a[1] * L // 100, hx + side * a[2] * L // 100, hy + a[3] * L // 100, max(1, a[4] * L // 100), mat, z, feat, snap=snap))
        elif k == "T":
            s.append(T(hx + side * a[0] * L // 100, hy + a[1] * L // 100, hx + side * a[2] * L // 100, hy + a[3] * L // 100,
                       hx + side * a[4] * L // 100, hy + a[5] * L // 100, mat, z, feat, snap=snap))
        elif k == "A":
            s.append(A(hx + side * a[0] * L // 100, hy + a[1] * L // 100, a[2] * L // 100, a[3] * L // 100, max(px, a[4] * L // 100), a[5], mat, z, feat, snap=snap))


# ---------------------------------------------------------------- signatures
SIGNATURE_ORDER = ("held", "headwear", "back", "beard", "top")


def signature(data: dict, g: dict) -> str:
    """The one feature that says who this is, drawn even at 8 px. A role can name
    it (`signature = "headwear"` in [role]); otherwise it is the first of: what
    they hold, what they wear on their head, what they carry on their back, a
    beard, their top."""
    sig = data.get("role", {}).get("signature")
    if sig:
        return sig
    if g["held"] != "none":
        return "held"
    if g["headwear"] != "none":
        return "headwear"
    if g["back"] != "none":
        return "back"
    if "beard" in g["accessories"]:
        return "beard"
    return "top"


# ---------------------------------------------------------------- render
def _materials(data: dict, g: dict) -> dict:
    pal = data["palette"]
    m = {k: pal["materials"][k] for k in pal["materials"]}
    m["cloth_a"] = pal["cloth"][g["cloth_a"]]
    m["cloth_b"] = pal["cloth"][g["cloth_b"]] if g["cloth_b"] in pal["cloth"] else pal["materials"]["leather"]
    m["hair"] = pal["hair"][g["hair_color"]]
    m["iris"] = pal["iris"][g["iris"]]
    return m


def visible_shapes(data: dict, g: dict, N: int, pose: dict | None = None, style_tier: int | None = None,
                   lod_tier: int | None = None, only_feats: tuple | None = None):
    """The shapes drawn at tier N: the LOD ladder, the role's signature promoted
    to the 8 px rung (snapped and on top below 32 px). Shared by every view."""
    px = D // N
    style_px = D // style_tier if style_tier else None
    sig = signature(data, g)
    sigs = (sig, sig + ".large")
    shapes = [sh for sh in build_shapes(g, px, pose or {}, style_px) if (8 if sh.feat in sigs else LOD.get(sh.feat, 8)) <= (lod_tier or N)
              and (only_feats is None or sh.feat in only_feats)]
    small = (style_tier or N) < 32
    for sh in shapes:  # below 32 px the signature is snapped to a whole pixel and drawn on top
        if sh.feat in sigs and small:
            sh.snap = True
            sh.z += 100
    return shapes, sigs


def shade_index(light: int, n: int, bands: int, dither: bool, x: int, y: int, bias: int) -> int:
    """A light value (-1024..1024) to a step on an n-colour ramp."""
    mid = (n - 1) // 2
    if bands == 1:
        idx = mid
    else:
        t16 = (light + 1024) * bands * 16 // 2049
        t = (t16 + (BAYER4[y % 4][x % 4] - 8) // 2) // 16 if dither else t16 // 16
        t = max(0, min(bands - 1, t))
        lo = max(0, min(n - bands, mid - (bands - 1) // 2)) if n >= bands else 0
        idx = min(n - 1, lo + t)
    return max(0, min(n - 1, idx + bias))


def finish(data: dict, g: dict, W: int, H: int, N: int, era: str, pix_mat: list, shade: list, depth: list,
           rim: bool = False, sig_mats: tuple = ()) -> Sprite:
    """Everything after the raster, shared by the front drawing and every 3D
    view: palette, contact shadows, the 8-bit eye rule, outline, era budget.
    `pix_mat` is each pixel's material ("" for empty), `shade` its ramp step,
    `depth` its distance (smaller is nearer) for contact shadows."""
    E_ = ERAS[era]
    mats = _materials(data, g)
    names = sorted(mats)
    # rim: a light outline for sprites that will sit on dark ground (Squint finds these)
    pal = [TRANSPARENT, hex_to_rgba(data["palette"].get("rim", "#e9e3cf") if rim else data["palette"].get("outline", "#140e10"))]
    offs, lens = {}, {}
    for nm in names:
        offs[nm] = len(pal)
        lens[nm] = len(mats[nm])
        pal += [hex_to_rgba(c) for c in mats[nm]]
    spr = Sprite(W, H, pal)
    shade = list(shade)
    # contact shadow: a pixel just below/beside a part that sits in front of it darkens one step
    if N >= 32:
        dark = []
        for y in range(H):
            for x in range(W):
                m = pix_mat[y * W + x]
                if m == "":
                    continue
                for dx, dy in ((0, -1), (-1, 0), (1, 0)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < W and 0 <= yy < H:
                        q = pix_mat[yy * W + xx]
                        if q != "" and depth[yy * W + xx] < depth[y * W + x] and q != m:
                            dark.append(y * W + x)
                            break
        for i in dark:
            shade[i] = max(0, shade[i] - 1)
    for i in range(W * H):
        m = pix_mat[i]
        if m != "":
            spr.px[i] = offs[m] + min(shade[i], lens[m] - 1)
            if era == "8-bit" and m in ("iris", "mouth"):
                spr.px[i] = 1  # NES practice: eyes and mouth in the outline colour, so they survive 3 colours
    # outline
    if N >= 16:
        rings = 2 if N >= 256 else 1
        selout = E_["outline"] == "selout" and N >= 32 and not rim
        filled = [m != "" for m in pix_mat]
        for ring in range(rings):
            marks = []
            for y in range(H):
                for x in range(W):
                    if filled[y * W + x]:
                        continue
                    for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < W and 0 <= yy < H and filled[yy * W + xx]:
                            m = pix_mat[yy * W + xx]
                            idx = 1
                            if selout and ring == 0 and m != "":
                                idx = offs[m]
                            marks.append((y * W + x, idx))
                            break
            for i, idx in marks:
                spr.px[i] = idx
                filled[i] = True
    heavy = set()
    for nm in ("iris",) + tuple(sig_mats):
        if nm in offs:
            heavy |= set(range(offs[nm], offs[nm] + lens[nm]))
    _era_reduce(spr, E_["max_colors"], reserve_outline=(era == "8-bit"), heavy=heavy)
    return spr


def render(data: dict, g: dict, tier: int, era: str | None = None, pose: dict | None = None, want_map: bool = False,
           style_tier: int | None = None, lod_tier: int | None = None, only_feats: tuple | None = None, rim: bool = False):
    """Draw genome g at a tier, from the front. Returns the sprite and the
    features that made it onto the canvas (the evidence for the character card)."""
    era = era or DEFAULT_CHAIN.get(tier, "hd")
    E_ = ERAS[era]
    N = tier
    px = D // N
    shapes, sigs = visible_shapes(data, g, N, pose, style_tier, lod_tier, only_feats)
    order = sorted(range(len(shapes)), key=lambda i: (shapes[i].z, i))
    owner = [-1] * (N * N)
    geo = []
    for i in order:
        sh = shapes[i]
        a = _snap(sh, px // 2)
        bx0, by0, bx1, by1 = _bbox(sh.kind, a)
        geo.append(a)
        x0, x1 = max(0, bx0 // px - 1), min(N - 1, bx1 // px + 1)
        y0, y1 = max(0, by0 // px - 1), min(N - 1, by1 // px + 1)
        for y in range(y0, y1 + 1):
            v = (2 * y + 1) * px // 2
            for x in range(x0, x1 + 1):
                u = (2 * x + 1) * px // 2
                if _inside(sh.kind, a, u, v):
                    owner[y * N + x] = len(geo) - 1
        sh.bbox = (bx0, by0, bx1, by1)
    drawn = [shapes[i] for i in order]
    lens = {k: len(v) for k, v in _materials(data, g).items()}
    bands = min(TIER_BANDS[N], E_["bands"])
    dither = E_["dither"] and N >= 128
    shade = [0] * (N * N)
    for y in range(N):
        v = (2 * y + 1) * px // 2
        for x in range(N):
            o = owner[y * N + x]
            if o < 0:
                continue
            sh = drawn[o]
            bx0, by0, bx1, by1 = sh.bbox
            hwid, hhei = max(1, (bx1 - bx0) // 2), max(1, (by1 - by0) // 2)
            u = (2 * x + 1) * px // 2
            nx = max(-1024, min(1024, (u - (bx0 + bx1) // 2) * 1024 // hwid))
            ny = max(-1024, min(1024, (v - (by0 + by1) // 2) * 1024 // hhei))
            z = isqrt(max(0, 1024 * 1024 - nx * nx - ny * ny))
            light = (-nx * 424 - ny * 566 + z * 707) // 1024
            shade[y * N + x] = shade_index(light, lens[sh.mat], bands, dither, x, y, sh.bias)
    pix_mat = [drawn[o].mat if o >= 0 else "" for o in owner]
    depth = [-o for o in owner]
    sig_mats = tuple(sorted({sh.mat for sh in drawn if sh.feat in sigs}))
    spr = finish(data, g, N, N, N, era, pix_mat, shade, depth, rim, sig_mats)
    feats = sorted({drawn[o].feat for o in owner if o >= 0})
    if want_map:
        return spr, feats, pix_mat, [drawn[o].feat if o >= 0 else "" for o in owner]
    return spr, feats


def _era_reduce(spr: Sprite, cap: int, reserve_outline: bool, heavy: set | None = None) -> None:
    """Merge colours until the era's per-sprite budget holds. Integer-only and
    deterministic: always merge the cheapest pair (weighted RGB distance times
    the smaller pixel count), keeping the more used colour. Identity colours
    (`heavy`: the iris and the role's signature) cost 8 times more to merge,
    so they are the last to go."""
    heavy = heavy or set()
    counts: dict[int, int] = {}
    for i in spr.px:
        if i:
            counts[i] = counts.get(i, 0) + 1
    keep = sorted(counts)
    locked = set()
    if reserve_outline and keep:
        lum = lambda i: 3 * spr.palette[i][0] + 6 * spr.palette[i][1] + spr.palette[i][2]
        locked.add(min(keep, key=lambda i: (lum(i), i)))
    remap = {i: i for i in keep}
    while len(keep) > cap:
        best = None
        for ai in range(len(keep)):
            for bi in range(ai + 1, len(keep)):
                a, b = keep[ai], keep[bi]
                if a in locked and b in locked:
                    continue
                ca, cb = spr.palette[a], spr.palette[b]
                d = 2 * (ca[0] - cb[0]) ** 2 + 4 * (ca[1] - cb[1]) ** 2 + 3 * (ca[2] - cb[2]) ** 2
                cost = d * min(counts[a], counts[b]) * (8 if a in heavy or b in heavy else 1)
                if best is None or cost < best[0]:
                    best = (cost, a, b)
        _, a, b = best
        if a in locked or (b not in locked and counts[a] >= counts[b]):
            win, lose = a, b
        else:
            win, lose = b, a
        counts[win] += counts.pop(lose)
        keep.remove(lose)
        for k, v in remap.items():
            if v == lose:
                remap[k] = win
    for p in range(len(spr.px)):
        i = spr.px[p]
        if i:
            spr.px[p] = remap[i]


# ---------------------------------------------------------------- public API
def streams_for(tf, seed: int, overrides=None) -> Streams:
    return Streams(master_seed(tf.type_hash, seed, ENGINE_MAJOR), overrides)


def stream_paths() -> list[str]:
    return ["g/body", "g/face", "g/hair", "g/outfit", "g/headwear", "g/items", "g/accessories"]


POSES = {
    "idle": [{}, {"bob": 1}, {"bob": 1, "blink": 1}, {}],
    "walk": [{"lift_l": 2, "swing": 1}, {"bob": 1}, {"lift_r": 2, "swing": -1}, {"bob": 1}],
}


def generate_frames(tf, seed: int, overrides=None, tier: int | None = None, era: str | None = None, anim: str = "idle"):
    data = tf.data
    g = genome(data, streams_for(tf, seed, overrides))
    t = tier or data.get("tier", 64)
    return [render(data, g, t, era, p)[0] for p in POSES[anim]]


def chain(tf, seed: int, tiers=TIERS, eras: dict | None = None, overrides=None):
    """The build bit chain: the same genome at every tier."""
    g = genome(tf.data, streams_for(tf, seed, overrides))
    out = []
    for t in tiers:
        era = (eras or DEFAULT_CHAIN).get(t, "hd")
        spr, feats = render(tf.data, g, t, era)
        out.append({"tier": t, "era": era, "sprite": spr, "features": feats, "colors": spr.used_colors()})
    return g, out


def coherence(data: dict, g: dict, tier: int, ref_tier: int = 256) -> dict:
    """How much tier `tier` still looks like the reference render: silhouette
    overlap (IoU) and material agreement, after reducing the reference to the
    same grid by majority vote. Integer percentages."""
    # same stylisation and same feature set as the small tier, drawn large:
    # what is left over is pure rasterisation loss
    big = render(data, g, ref_tier, want_map=True, style_tier=tier, lod_tier=tier)[2]
    small = render(data, g, tier, want_map=True)[2]
    k = ref_tier // tier
    inter = union = agree = both = 0
    for y in range(tier):
        for x in range(tier):
            votes: dict = {}
            for yy in range(y * k, y * k + k):
                for xx in range(x * k, x * k + k):
                    m = big[yy * ref_tier + xx]
                    votes[m] = votes.get(m, 0) + 1
            mref = max(sorted(votes), key=lambda m: votes[m])
            ms = small[y * tier + x]
            a, b = mref != "", ms != ""
            inter += a and b
            union += a or b
            if a and b:
                both += 1
                agree += mref == ms
    return {"tier": tier, "iou": inter * 100 // max(1, union), "material": agree * 100 // max(1, both)}


POW2_16 = [4096, 4277, 4467, 4664, 4871, 5087, 5312, 5547, 5793, 6049, 6317, 6597, 6889, 7194, 7512, 7845]  # 2^(i/16) x4096


def zoom_plan(from_tier, to_tier, steps):
    """A smooth zoom between two chain tiers: for each frame, the display size
    and the two tiers dissolved into it, with the share (0..16) of the larger.
    Sizes grow geometrically, so the zoom feels even."""
    doublings = 0
    t = from_tier
    while t < to_tier:
        t *= 2
        doublings += 1
    plan = []
    for k in range(steps):
        e = k * doublings * 16 // max(1, steps - 1)  # sixteenths of a doubling
        size = from_tier * (1 << (e // 16)) * POW2_16[e % 16] // 4096
        size = min(to_tier, max(from_tier, size))
        a = from_tier
        while a * 2 <= size and a * 2 <= to_tier:
            a *= 2
        b = min(to_tier, a * 2)
        w = 16 if a == size and b == a else (size - a) * 16 // a
        if b == a:
            w = 0
        plan.append([size, a, b, min(16, w)])
    return plan


LEG_FEATS = ("legs", "feet", "bottom")


def legs_visible(g: dict) -> bool:
    return g["top"] not in ("robe", "dress", "cloak") and g["bottom"] not in ("skirt",) and g["back"] != "cape"


def leg_count(featmap: list, N: int) -> int:
    """Separate legs standing on the ground. Only transparent gaps separate
    legs; a held item drawn across a leg does not split it, and a run of
    pixels with no leg, foot or trouser pixel in it (a hanging item) is not a
    leg."""
    rows = [y for y in range(N) if any(featmap[y * N + x] in LEG_FEATS for x in range(N))]
    if not rows:
        return 0
    counts = []
    for y in (rows[-3:-1] if len(rows) >= 3 else rows):
        runs, inside, has_leg = 0, False, False
        for x in range(N + 1):
            f = featmap[y * N + x] if x < N else ""
            if f != "":
                has_leg = has_leg or f in LEG_FEATS
                inside = True
            else:
                if inside and has_leg:
                    runs += 1
                inside, has_leg = False, False
        counts.append(runs)
    # the clearest row in the band: a hip row joined by an apron hides legs,
    # while a third leg or merged legs show in every row of the band
    return max(counts)


def legs_check(data: dict, g: dict, tier: int) -> dict:
    """Two promises: drawn alone, the legs are exactly two with a gap
    (construction); with everything drawn, no more than two legs show
    (a held item may hide one, never add one)."""
    alone = leg_count(render(data, g, tier, want_map=True, only_feats=("legs", "feet"))[3], tier)
    shown = leg_count(render(data, g, tier, want_map=True)[3], tier) if legs_visible(g) else None
    ok = alone == 2 and (shown is None or 1 <= shown <= 2)
    return {"tier": tier, "alone": alone, "shown": shown, "ok": ok}
