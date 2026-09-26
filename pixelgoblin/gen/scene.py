"""Scene composer — a whole place, with its people, from one type file.

A scene is layered like a stage set, back to front:

  sky -> far cliffs (with waterfalls) -> tree canopy -> platforms with huts,
  bridges and lanterns -> mid ground -> water -> market stalls -> ground

and its crowd is made of real rig characters drawn at a DEPTH TIER: far
goblins at 16 px, middle ones at 32, near ones at 64 (or whatever the type
file says). A distant goblin is therefore still a goblin with ears, eyes and
a job, not a smudge — which is how background characters keep their quality.

Integer-only. A scene's identity is its own type hash PLUS the hashes of every
type file it pulls characters from, so editing a role file changes the scene's
seed stream as it should.
"""

from __future__ import annotations

from .. import ENGINE_MAJOR
from ..rng import M32, Streams, hash32, master_seed, sha256
from ..sprite import TRANSPARENT, Sprite, blit, hex_to_rgba
from . import rig
from .parallax import BAYER4, noise1d


def identity(tf) -> str:
    from ..typefile import load
    refs = sorted({r for d in tf.data["crowd"] for r in d["roles"]})
    parts = [tf.type_hash] + [load(r).type_hash for r in refs]
    return sha256("".join(parts).encode()).hex()


class _Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.spr = Sprite(w, h, [TRANSPARENT])
        self.ramps: dict = {}

    def ramp(self, name, colors):
        if name not in self.ramps:
            self.ramps[name] = len(self.spr.palette)
            self.spr.palette += [hex_to_rgba(c) for c in colors]
        return self.ramps[name]

    def put(self, x, y, i):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.spr.px[y * self.w + x] = i

    def rect(self, x0, y0, x1, y1, i):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.spr.px[y * self.w + x] = i

    def ellipse(self, cx, cy, rx, ry, i):
        for y in range(max(0, cy - ry), min(self.h, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(self.w, cx + rx + 1)):
                dx, dy = x - cx, y - cy
                if dx * dx * ry * ry + dy * dy * rx * rx <= rx * rx * ry * ry:
                    self.spr.px[y * self.w + x] = i

    def tri(self, x0, y0, x1, y1, x2, y2, i):
        for y in range(max(0, min(y0, y1, y2)), min(self.h, max(y0, y1, y2) + 1)):
            for x in range(max(0, min(x0, x1, x2)), min(self.w, max(x0, x1, x2) + 1)):
                d0 = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)
                d1 = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
                d2 = (x0 - x2) * (y - y2) - (y0 - y2) * (x - x2)
                if (d0 >= 0 and d1 >= 0 and d2 >= 0) or (d0 <= 0 and d1 <= 0 and d2 <= 0):
                    self.spr.px[y * self.w + x] = i


# ---------------------------------------------------------------- prop detail by size
# Props follow the characters' rule: detail arrives with size, it is never
# smeared. A hut gains a door at 14 px wide, planks and a framed window at 20,
# roof shingles at 32; a stall gains a scalloped awning and crates at 60.
PROP_LOD = {"door": 14, "planks": 20, "window_frame": 20, "shingles": 32, "scallops": 60, "crates": 60}


def _hut_detail(cv, px_, py, hw, hh, wd, nwd, rf, nrf):
    if hw >= PROP_LOD["planks"]:
        for yy in range(py - hh + 2, py, 3):
            cv.rect(px_ - hw // 2 + 1, yy, px_ + hw // 2 - 1, yy + 1, wd + max(0, nwd - 4))
    if hw >= PROP_LOD["window_frame"]:
        y0, y1 = py - hh * 6 // 10, py - hh * 2 // 10
        cv.rect(px_ - 2, y0 - 1, px_ + 3, y0, wd)
        cv.rect(px_ - 2, y1, px_ + 3, y1 + 1, wd)
        cv.rect(px_ - 2, y0, px_ - 1, y1, wd)
        cv.rect(px_ + 2, y0, px_ + 3, y1, wd)
    if hw >= PROP_LOD["door"]:
        dx = px_ + hw // 4
        cv.rect(dx, py - hh * 55 // 100, dx + max(2, hw // 6), py, wd + 1)
    if hw >= PROP_LOD["shingles"]:
        top = py - hh - hh * 7 // 10
        for yy in range(top + 3, py - hh, 3):
            half = (yy - top) * (hw * 7 // 10) // max(1, hh * 7 // 10)
            for x in range(px_ - half + 1, px_ + half):
                if (x + yy) % 4 == 0:
                    cv.put(x, yy, rf + max(0, nrf - 4))


def _stall_detail(cv, sx, sy, sw, H, aw, wd):
    if sw >= PROP_LOD["scallops"]:
        yb = sy - H // 5 + H // 40
        for x in range(sx - 2, sx + sw + 2):
            if (x - sx) % 4 < 2:
                cv.put(x, yb, aw + 1)
    if sw >= PROP_LOD["crates"]:
        for k in range(sw // 12):
            cx = sx + 3 + k * 12
            cv.rect(cx, sy - 5, cx + 5, sy - 1, wd + 2)
            cv.rect(cx, sy - 5, cx + 5, sy - 4, wd + 3)


def generate(tf, seed: int, overrides=None) -> Sprite:
    return generate_frames(tf, seed, overrides)[0]


def generate_frames(tf, seed: int, overrides=None, population=None) -> list[Sprite]:
    """`population` (from city.census) replaces the random crowd with named
    citizens: dicts with role, seed, band, and optional overrides, sub, team."""
    from ..typefile import compose, load, with_team
    d = tf.data
    W, H = d["size"]
    S = Streams(master_seed(identity(tf), seed, ENGINE_MAJOR), overrides)
    P = d["palette"]
    cv = _Canvas(W, H)
    sky = cv.ramp("sky", P["sky"])
    n = len(P["sky"])
    # sky: vertical bands, ordered dither, light at the horizon
    for y in range(H):
        for x in range(W):
            band = y * (n - 1) * 16 // max(1, H * 6 // 10)
            b, f = min(n - 1, band // 16), band % 16
            idx = b + 1 if f > BAYER4[y % 4][x % 4] and b + 1 <= n - 1 else b
            cv.spr.px[y * W + x] = sky + min(n - 1, idx)
    # clouds
    cl = cv.ramp("cloud", P["cloud"])
    r = S.rng("clouds")
    for _ in range(d.get("clouds", 4)):
        cx, cy = r.below(W), H // 20 + r.below(H // 5)
        for k in range(4):
            cv.ellipse(cx + (k - 2) * W // 40, cy + (k % 2) * H // 60, W // 30 + r.below(W // 40 + 1), H // 40 + 1, cl + (len(P["cloud"]) - 1 if k % 2 else len(P["cloud"]) - 2))
    # far cliffs: two noise ridges, the nearer one darker
    for li, (base, amp, mat) in enumerate(((42, 14, "cliff_far"), (56, 12, "cliff"))):
        o = cv.ramp(mat, P[mat])
        m = len(P[mat])
        seed_l = S.rng(f"ridge/{li}").next()
        for x in range(W):
            top = H * base // 100 - noise1d(seed_l, x, [W // 5 + 1, W // 16 + 2], [H * amp // 100, H * amp // 300])
            for y in range(max(0, top), H):
                depth = y - top
                shade = m - 1 if depth < 2 else max(0, m - 2 - (depth * (m - 1) // max(1, H - top)) - (1 if hash32(seed_l ^ ((x * 0x9E3779B1) & M32) ^ ((y * 0x85EBCA6B) & M32)) % 9 == 0 else 0))
                cv.spr.px[y * W + x] = o + shade
    # waterfalls
    wa = cv.ramp("water", P["water"])
    nw = len(P["water"])
    rw = S.rng("falls")
    falls = []
    for i in range(d.get("waterfalls", 3)):
        fx = W * (15 + i * 70 // max(1, d.get("waterfalls", 3))) // 100 + rw.below(W // 12)
        fw = max(2, W // 80 + rw.below(W // 90 + 1))
        ftop = H * (30 + rw.below(14)) // 100
        falls.append((fx, fw))
        for y in range(ftop, H * 74 // 100):
            for x in range(fx, fx + fw):
                streak = (y * 3 + x * 7 + hash32(x * 131 + i)) % 11
                cv.put(x, y, wa + (nw - 1 if streak < 3 else nw - 2 if streak < 7 else nw - 3))
        cv.ellipse(fx + fw // 2, H * 74 // 100, fw * 2, max(1, H // 60), wa + nw - 1)
    # tree canopy along the cliffs
    lf = cv.ramp("leaf", P["leaf"])
    nl = len(P["leaf"])
    tr = cv.ramp("trunk", P["trunk"])
    rt = S.rng("trees")
    for i in range(d.get("trees", 10)):
        tx = rt.below(W)
        ty = H * (38 + rt.below(20)) // 100
        cv.rect(tx - 1, ty, tx + 1, ty + H // 8, tr + 1)
        for k in range(5):
            rr = W // 40 + rt.below(W // 50 + 1)
            cv.ellipse(tx + (k - 2) * rr // 2, ty - (k % 3) * rr // 3, rr, rr * 3 // 4, lf + max(0, nl - 1 - (k % 3)))
    # platforms with huts, bridges and lanterns
    wd = cv.ramp("wood", P["wood"])
    nwd = len(P["wood"])
    rf = cv.ramp("roof", P["roof"])
    gl = cv.ramp("glow", P["glow"])
    ng = len(P["glow"])
    rp = S.rng("platforms")
    plats = []
    for i in range(d.get("huts", 5)):
        px_ = W * (8 + i * 84 // max(1, d.get("huts", 5))) // 100 + rp.below(W // 20)
        py = H * (40 + rp.below(22)) // 100
        pw = W // 12 + rp.below(W // 16)
        plats.append((px_, py, pw))
        cv.rect(px_ - pw // 2, py, px_ + pw // 2, py + 2, wd + nwd - 2)
        for sx in (px_ - pw // 2 + 1, px_ + pw // 2 - 2):
            cv.rect(sx, py + 2, sx + 1, py + H // 7, wd + 1)
        hw, hh = pw * 6 // 10, H // 14 + rp.below(H // 30)
        cv.rect(px_ - hw // 2, py - hh, px_ + hw // 2, py, wd + nwd - 3)
        cv.tri(px_ - hw * 7 // 10, py - hh, px_ + hw * 7 // 10, py - hh, px_, py - hh - hh * 7 // 10, rf + len(P["roof"]) - 2)
        cv.tri(px_ - hw * 7 // 10, py - hh, px_, py - hh, px_, py - hh - hh * 7 // 10, rf + len(P["roof"]) - 3)
        cv.rect(px_ - 1, py - hh * 6 // 10, px_ + 2, py - hh * 2 // 10, gl + ng - 2)
        _hut_detail(cv, px_, py, hw, hh, wd, nwd, rf, len(P["roof"]))
        # lantern
        lx = px_ + pw // 2 - 1
        cv.put(lx, py - 3, wd)
        cv.ellipse(lx, py - 1, 1, 1, gl + ng - 1)
    for a, b in zip(plats, plats[1:]):
        if abs(a[1] - b[1]) < H // 6:
            x0, x1 = a[0] + a[2] // 2, b[0] - b[2] // 2
            for x in range(x0, x1):
                t = (x - x0) * 1024 // max(1, x1 - x0)
                sag = (t * (1024 - t)) * (H // 40 + 1) // (1024 * 256)
                y = a[1] + (b[1] - a[1]) * t // 1024 + sag
                cv.put(x, y, wd + nwd - 2)
                cv.put(x, y + 1, wd + 1)
                if x % 4 == 0:
                    cv.put(x, y - 1, wd + 2)
    # water pool
    for y in range(H * 74 // 100, H * 82 // 100):
        for x in range(W):
            band = 1 if (x + y * 2) % 13 == 0 else 0
            cv.spr.px[y * W + x] = wa + max(0, nw - 3 + band - (y - H * 74 // 100) * 2 // max(1, H * 8 // 100))
    # ground
    gd = cv.ramp("ground", P["ground"])
    ngd = len(P["ground"])
    for y in range(H * 82 // 100, H):
        for x in range(W):
            h = hash32(x * 7919 ^ y * 104729) % 23
            cv.spr.px[y * W + x] = gd + (ngd - 1 if y == H * 82 // 100 else ngd - 2 if h == 0 else 1 if h == 1 else ngd - 3)
    # market stalls
    cl2 = [cv.ramp(f"awning{i}", c) for i, c in enumerate(P["awnings"])]
    rs = S.rng("stalls")
    for i in range(d.get("stalls", 3)):
        sx = W * (6 + i * 88 // max(1, d.get("stalls", 3))) // 100 + rs.below(W // 20)
        sw = W // 8 + rs.below(W // 20)
        sy = H * 80 // 100
        aw = cl2[rs.below(len(cl2))]
        cv.rect(sx, sy - H // 5, sx + 2, sy + H // 12, wd + 1)
        cv.rect(sx + sw - 2, sy - H // 5, sx + sw, sy + H // 12, wd + 1)
        for x in range(sx - 2, sx + sw + 2):
            for y in range(sy - H // 5 - H // 30, sy - H // 5 + H // 40):
                cv.put(x, y, aw + (3 if (x - sx) // max(2, W // 64) % 2 else 1))
        cv.rect(sx, sy, sx + sw, sy + H // 20, wd + nwd - 2)
        for k in range(sw // 3):
            cv.put(sx + 1 + k * 3, sy - 1, cl2[(k + i) % len(cl2)] + 3)
            cv.put(sx + 2 + k * 3, sy - 1, gl + ng - 2)
        cv.ellipse(sx + sw // 2, sy - H // 5 + H // 20, 1, 2, gl + ng - 1)
        _stall_detail(cv, sx, sy, sw, H, aw, wd)
    # the crowd, at depth tiers
    for band in d["crowd"]:
        rc = S.rng(f"crowd/{band['name']}")
        tier = band["tier"]
        y_lo, y_hi = H * band["y"][0] // 100, H * band["y"][1] // 100
        placed = []
        pool: list = []
        people = [p for p in population if p["band"] == band["name"]] if population is not None else None
        for k in range(band["count"] if people is None else len(people)):
            if people is None:
                if not pool:  # every role appears once before any repeats
                    pool = list(band["roles"])
                role = pool.pop(rc.below(len(pool)))
                ctf = load(role)
                cseed = rc.next()
                over = None
            else:
                who = people[k]
                ctf = compose(who["role"], who["sub"]) if who.get("sub") else load(who["role"])
                if who.get("team"):
                    ctf = with_team(ctf, who["team"])
                cseed, over = who["seed"], who.get("overrides")
            g = rig.genome(ctf.data, rig.streams_for(ctf, cseed, over))
            spr, _ = rig.render(ctf.data, g, tier, band.get("era"))
            if band.get("on") == "platforms" and plats:
                pl = plats[rc.below(len(plats))]
                x = pl[0] - pl[2] // 2 + rc.below(max(1, pl[2])) - tier // 2
                y = pl[1] - tier + tier // 16
            else:
                x = rc.below(max(1, W - tier // 2)) - tier // 4
                y = y_lo + rc.below(max(1, y_hi - y_lo + 1)) - tier
            placed.append((y, x, spr))
        for y, x, spr in sorted(placed, key=lambda t: (t[0], t[1])):
            blit(cv.spr, spr, x, y)
    return [cv.spr]
