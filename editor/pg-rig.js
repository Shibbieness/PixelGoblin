/* PixelGoblin rig + scene — JavaScript port of pixelgoblin/gen/{rig,scene}.py.
   Built on PixelGoblin — © Shibbieness / M MAOU LLC · AGPL-3.0-or-later
   The character GEOMETRY (build_shapes and its helpers) is not hand-written:
   tools/transpile_rig.py generates it from the Python source and it is spliced
   in at the marker below. This file holds the runtime around it — genome,
   rasteriser, shading, outline, era reduction, poses, scene composer — written
   line for line against the Python. Build gate B13 compares pixels at every
   tier. Integer-only: F() and MOD() are Python floor division and modulo. */
const PGRig = ((PG) => {
  "use strict";
  // ---------------------------------------------------------------- python integer semantics
  function F(a, b) {
    let q = Math.floor(a / b);
    const r = a - q * b;
    if (b > 0 ? r < 0 : r > 0) q -= 1;
    else if (b > 0 ? r >= b : r <= b) q += 1;
    return q;
  }
  const MOD = (a, b) => a - F(a, b) * b;
  const get = (o, k, d) => (o && o[k] !== undefined && o[k] !== null ? o[k] : d);
  const cmpStr = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  // ---------------------------------------------------------------- constants (mirror rig.py)
  const TIERS = [8, 16, 32, 64, 128, 256];
  const D = 1024, CX = 512, GROUND = 1000;
  const BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
  const LOD = {
    body: 8, head: 8, ears: 8, legs: 8, arms: 8, torso: 8,
    "held.large": 8, "headwear.large": 8, "back.large": 8,
    top: 8, bottom: 8, hair: 8, feet: 8,
    eyes: 16, held: 16, headwear: 16, back: 16,
    beard: 16, belt: 16, glasses: 16, goggles: 16, pauldrons: 16, fins: 16,
    mouth: 32, nose: 32, hands: 32, sleeves: 32, scarf: 32, earrings: 32, buckle: 32,
    brows: 64, eye_whites: 64, ear_inner: 64, necklace: 64, tusks: 64, pouches: 64, bracers: 64,
    tongue: 64, flowers: 64, straps: 64,
    pupils: 128, highlights: 128, pattern: 128, stitches: 128, fur_tufts: 128, nails: 128,
  };
  const TIER_BANDS = { 8: 1, 16: 2, 32: 3, 64: 4, 128: 5, 256: 5 };
  const TIER_HEAD = { 8: 14, 16: 8, 32: 4, 64: 1, 128: 0, 256: 0 };
  const TIER_EYE = { 8: 0, 16: 40, 32: 25, 64: 10, 128: 0, 256: 0 };
  const ERAS = {
    "8-bit": { max_colors: 3, bands: 2, dither: false, outline: "plain", why: "NES-class: 3 colours + transparent per sprite" },
    "16-bit": { max_colors: 15, bands: 3, dither: false, outline: "selout", why: "SNES/Genesis-class: 15 colours + transparent per sprite palette" },
    "32-bit": { max_colors: 31, bands: 4, dither: false, outline: "selout", why: "GBA/PS1-class 2D: larger palettes, smoother ramps" },
    hd: { max_colors: 255, bands: 5, dither: true, outline: "selout", why: "modern HD pixel art: full ramps, ordered dithering" },
  };
  const DEFAULT_CHAIN = { 8: "8-bit", 16: "16-bit", 32: "16-bit", 64: "32-bit", 128: "hd", 256: "hd" };
  const AGES = { child: [520, 600, 44, 22], teen: [660, 720, 38, 25], adult: [740, 810, 36, 25], elder: [700, 770, 37, 24] };
  const BUILDS = { slim: 78, average: 92, stocky: 110, heavy: 128 };
  const EXPRESSIONS = ["neutral", "happy", "curious", "confident", "thoughtful", "annoyed", "angry", "surprised", "playful"];

  // ---------------------------------------------------------------- integer shapes
  const shape = (kind, a, mat, z, feat, o) => ({ kind, a, mat, z, feat, bias: get(o, "bias", 0), snap: get(o, "snap", false), bbox: null });
  const E = (cx, cy, rx, ry, mat, z, feat, o) => shape("E", [cx, cy, rx, ry], mat, z, feat, o);
  const R = (x0, y0, x1, y1, rad, mat, z, feat, o) => shape("R", [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1), rad], mat, z, feat, o);
  const C = (x0, y0, x1, y1, r, mat, z, feat, o) => shape("C", [x0, y0, x1, y1, r], mat, z, feat, o);
  const T = (x0, y0, x1, y1, x2, y2, mat, z, feat, o) => shape("T", [x0, y0, x1, y1, x2, y2], mat, z, feat, o);
  const A = (cx, cy, rx, ry, th, half, mat, z, feat, o) => shape("A", [cx, cy, rx, ry, th, half], mat, z, feat, o);

  function _snap(s, halfpx) {
    let a = s.a.slice();
    if (!s.snap) return a;
    if (s.kind === "E") { a[2] = Math.max(a[2], halfpx); a[3] = Math.max(a[3], halfpx); }
    else if (s.kind === "C") a[4] = Math.max(a[4], halfpx);
    else if (s.kind === "R") {
      if (a[2] - a[0] < 2 * halfpx) { const m = F(a[0] + a[2], 2); a[0] = m - halfpx; a[2] = m + halfpx; }
      if (a[3] - a[1] < 2 * halfpx) { const m = F(a[1] + a[3], 2); a[1] = m - halfpx; a[3] = m + halfpx; }
    } else if (s.kind === "A") a[4] = Math.max(a[4], 2 * halfpx);
    else if (s.kind === "T") a = a.concat([halfpx]);
    return a;
  }
  function _bbox(kind, a) {
    if (kind === "E") return [a[0] - a[2], a[1] - a[3], a[0] + a[2], a[1] + a[3]];
    if (kind === "R") return [a[0], a[1], a[2], a[3]];
    if (kind === "C") return [Math.min(a[0], a[2]) - a[4], Math.min(a[1], a[3]) - a[4], Math.max(a[0], a[2]) + a[4], Math.max(a[1], a[3]) + a[4]];
    if (kind === "T") {
      const xs = [a[0], a[2], a[4]], ys = [a[1], a[3], a[5]], pad = a.length === 7 ? a[6] : 0;
      return [Math.min(...xs) - pad, Math.min(...ys) - pad, Math.max(...xs) + pad, Math.max(...ys) + pad];
    }
    return [a[0] - a[2], a[1] - a[3], a[0] + a[2], a[1] + a[3]];
  }
  function _inside(kind, a, u, v) {
    if (kind === "E") {
      const dx = u - a[0], dy = v - a[1], rx = a[2], ry = a[3];
      if (rx <= 0 || ry <= 0) return false;
      return dx * dx * ry * ry + dy * dy * rx * rx <= rx * rx * ry * ry;
    }
    if (kind === "R") {
      const [x0, y0, x1, y1] = a;
      if (u < x0 || u > x1 || v < y0 || v > y1) return false;
      const r = Math.min(a[4], F(x1 - x0, 2), F(y1 - y0, 2));
      const dx = Math.max(x0 + r - u, 0, u - (x1 - r)), dy = Math.max(y0 + r - v, 0, v - (y1 - r));
      return dx * dx + dy * dy <= r * r;
    }
    if (kind === "C") {
      const [x0, y0, x1, y1, r] = a;
      const dx = x1 - x0, dy = y1 - y0, px = u - x0, py = v - y0;
      const len2 = dx * dx + dy * dy, dot = px * dx + py * dy;
      if (len2 === 0 || dot <= 0) return px * px + py * py <= r * r;
      if (dot >= len2) { const qx = u - x1, qy = v - y1; return qx * qx + qy * qy <= r * r; }
      return (px * px + py * py) * len2 - dot * dot <= r * r * len2;
    }
    if (kind === "T") {
      const [x0, y0, x1, y1, x2, y2] = a;
      if (a.length === 7 && _inside("C", [F(x0 + x1, 2), F(y0 + y1, 2), x2, y2, a[6]], u, v)) return true;
      const d0 = (x1 - x0) * (v - y0) - (y1 - y0) * (u - x0);
      const d1 = (x2 - x1) * (v - y1) - (y2 - y1) * (u - x1);
      const d2 = (x0 - x2) * (v - y2) - (y0 - y2) * (u - x2);
      return (d0 >= 0 && d1 >= 0 && d2 >= 0) || (d0 <= 0 && d1 <= 0 && d2 <= 0);
    }
    const [cx, cy, rx, ry, th, half] = a;
    if ((half === 1 && v < cy) || (half === -1 && v > cy)) return false;
    const dx = u - cx, dy = v - cy;
    if (rx <= 0 || ry <= 0) return false;
    if (dx * dx * ry * ry + dy * dy * rx * rx > rx * rx * ry * ry) return false;
    const irx = rx - th, iry = ry - th;
    if (irx <= 0 || iry <= 0) return true;
    return dx * dx * iry * iry + dy * dy * irx * irx > irx * irx * iry * iry;
  }
  function isqrt(n) {
    if (n <= 0) return 0;
    let r = Math.floor(Math.sqrt(n));
    while (r * r > n) r -= 1;
    while ((r + 1) * (r + 1) <= n) r += 1;
    return r;
  }

  // ---------------------------------------------------------------- genome
  const _pick = (rng, options, dflt = "none") => (!options || options.length === 0 ? dflt : options[rng.below(options.length)]);
  const _rngRange = (rng, [lo, hi]) => (hi > lo ? lo + rng.below(hi - lo + 1) : lo);
  function genome(data, S) {
    const sp = get(data, "species", {}), role = get(data, "role", {});
    const b = S.rng("g/body");
    const age = _pick(b, get(role, "age", ["adult"]), "adult");
    const [hLo, hHi, headPct, legPct] = AGES[age];
    const g = { age };
    g.height = _rngRange(b, [hLo, hHi]);
    g.head_pct = headPct + _rngRange(b, get(sp, "head_adj", [-2, 2]));
    g.head_w_pct = _rngRange(b, get(sp, "head_w", [92, 104]));
    g.build = _pick(b, get(role, "build", get(sp, "build", ["average"])), "average");
    g.ear_len = _rngRange(b, get(sp, "ear_len", [60, 100]));
    g.ear_lift = _rngRange(b, get(sp, "ear_lift", [-15, 25]));
    g.ear_w = _rngRange(b, get(sp, "ear_w", [26, 34]));
    g.nose = _rngRange(b, get(sp, "nose", [90, 130]));
    g.eye = _rngRange(b, get(sp, "eye", [100, 120]));
    g.leg_pct = legPct;
    g.hunch = age === "elder" ? 1 : 0;
    const f = S.rng("g/face");
    g.expression = _pick(f, get(role, "expression", ["neutral"]), "neutral");
    g.iris = _pick(f, get(sp, "iris", ["amber"]), "amber");
    const h = S.rng("g/hair");
    g.hair = _pick(h, get(role, "hair", get(sp, "hair", ["short"])), "none");
    g.hair_color = _pick(h, get(role, "hair_color", get(sp, "hair_color", ["black"])), "black");
    const o = S.rng("g/outfit");
    g.top = _pick(o, get(role, "top", ["tunic"]));
    g.bottom = _pick(o, get(role, "bottom", ["trousers"]));
    g.cloth_a = _pick(o, get(role, "cloth_a", ["red"]), "red");
    g.cloth_b = _pick(o, get(role, "cloth_b", ["leather"]), "leather");
    const hw = S.rng("g/headwear");
    g.headwear = _pick(hw, get(role, "headwear", ["none"]));
    const it = S.rng("g/items");
    g.held = _pick(it, get(role, "held", ["none"]));
    g.offhand = _pick(it, get(role, "offhand", ["none"]));
    g.back = _pick(it, get(role, "back", ["none"]));
    const items = get(data, "items", {});
    for (const slot of ["held", "offhand"]) if (Object.prototype.hasOwnProperty.call(items, g[slot])) g[slot + "_spec"] = items[g[slot]].shapes;
    const ac = S.rng("g/accessories");
    const acc = [];
    for (const entry of get(role, "accessories", []).concat(get(sp, "accessories", []))) {
      if (ac.chance(get(entry, "chance", 100))) acc.push(entry.item);
    }
    g.accessories = Array.from(new Set(acc)).sort(cmpStr);
    const team = get(data, "team", null);
    if (team) { g.cloth_a = team.a; g.cloth_b = team.b; g.team = team.name; }
    return g;
  }

  // ---------------------------------------------------------------- geometry (generated)
  /*__RIG_GEN__*/

  // ---------------------------------------------------------------- render
  function _materials(data, g) {
    const pal = data.palette, m = {};
    for (const k of Object.keys(pal.materials)) m[k] = pal.materials[k];
    m.cloth_a = pal.cloth[g.cloth_a];
    m.cloth_b = g.cloth_b in pal.cloth ? pal.cloth[g.cloth_b] : pal.materials.leather;
    m.hair = pal.hair[g.hair_color];
    m.iris = pal.iris[g.iris];
    return m;
  }
  // shapes drawn at tier N: the LOD ladder, the signature promoted to 8 px (rig.visible_shapes)
  function visibleShapes(data, g, N, pose, styleTier, lodTier, only) {
    const px = F(D, N), style_px = styleTier ? F(D, styleTier) : null;
    const sig = signature(data, g), sigs = [sig, sig + ".large"];
    const shapes = build_shapes(g, px, pose || {}, style_px).filter((sh) => (sigs.includes(sh.feat) ? 8 : get(LOD, sh.feat, 8)) <= (lodTier || N) && (!only || only.includes(sh.feat)));
    const small = (styleTier || N) < 32;
    for (const sh of shapes) if (sigs.includes(sh.feat) && small) { sh.snap = true; sh.z += 100; }
    return { shapes, sigs };
  }
  // everything after the raster, shared by the front drawing and every view (rig.finish)
  function finish(data, g, W, H, N, era, pixMat, shade, depth, rim, sigMats) {
    const E_ = ERAS[era];
    const mats = _materials(data, g), names = Object.keys(mats).sort(cmpStr);
    const pal = [[0, 0, 0, 0], PG.hexToRgba(rim ? get(data.palette, "rim", "#e9e3cf") : get(data.palette, "outline", "#140e10"))];
    const offs = {}, lens = {};
    for (const nm of names) { offs[nm] = pal.length; lens[nm] = mats[nm].length; for (const c of mats[nm]) pal.push(PG.hexToRgba(c)); }
    const spr = new PG.Sprite(W, H, pal);
    shade = Array.from(shade);
    if (N >= 32) {
      const dark = [];
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const m = pixMat[y * W + x];
        if (m === "") continue;
        for (const [dx, dy] of [[0, -1], [-1, 0], [1, 0]]) {
          const xx = x + dx, yy = y + dy;
          if (xx >= 0 && xx < W && yy >= 0 && yy < H) {
            const q = pixMat[yy * W + xx];
            if (q !== "" && depth[yy * W + xx] < depth[y * W + x] && q !== m) { dark.push(y * W + x); break; }
          }
        }
      }
      for (const i of dark) shade[i] = Math.max(0, shade[i] - 1);
    }
    for (let i = 0; i < W * H; i++) {
      const m = pixMat[i];
      if (m !== "") {
        spr.px[i] = offs[m] + Math.min(shade[i], lens[m] - 1);
        if (era === "8-bit" && (m === "iris" || m === "mouth")) spr.px[i] = 1;
      }
    }
    if (N >= 16) {
      const rings = N >= 256 ? 2 : 1;
      const selout = E_.outline === "selout" && N >= 32 && !rim;
      const filled = Array.from(pixMat, (m) => m !== "");
      for (let ring = 0; ring < rings; ring++) {
        const marks = [];
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
          if (filled[y * W + x]) continue;
          for (const [dx, dy] of [[0, -1], [-1, 0], [1, 0], [0, 1]]) {
            const xx = x + dx, yy = y + dy;
            if (xx >= 0 && xx < W && yy >= 0 && yy < H && filled[yy * W + xx]) {
              const m = pixMat[yy * W + xx];
              let idx = 1;
              if (selout && ring === 0 && m !== "") idx = offs[m];
              marks.push([y * W + x, idx]);
              break;
            }
          }
        }
        for (const [i, idx] of marks) { spr.px[i] = idx; filled[i] = true; }
      }
    }
    const heavy = new Set();
    for (const nm of ["iris"].concat(sigMats || [])) if (nm in offs) for (let k = 0; k < lens[nm]; k++) heavy.add(offs[nm] + k);
    _eraReduce(spr, E_.max_colors, era === "8-bit", heavy);
    return spr;
  }
  function render(data, g, tier, opts = {}) {
    const era = opts.era || get(DEFAULT_CHAIN, tier, "hd");
    const E_ = ERAS[era];
    const N = tier, px = F(D, N);
    const vis = visibleShapes(data, g, N, opts.pose, opts.style_tier || null, opts.lod_tier || null, opts.only_feats || null);
    const shapes = vis.shapes;
    const order = shapes.map((_, i) => i).sort((i, j) => shapes[i].z - shapes[j].z || i - j);
    const owner = new Int32Array(N * N).fill(-1);
    const geo = [];
    for (const i of order) {
      const sh = shapes[i];
      const a = _snap(sh, F(px, 2));
      const [bx0, by0, bx1, by1] = _bbox(sh.kind, a);
      geo.push(a);
      const x0 = Math.max(0, F(bx0, px) - 1), x1 = Math.min(N - 1, F(bx1, px) + 1);
      const y0 = Math.max(0, F(by0, px) - 1), y1 = Math.min(N - 1, F(by1, px) + 1);
      for (let y = y0; y <= y1; y++) {
        const v = F((2 * y + 1) * px, 2);
        for (let x = x0; x <= x1; x++) {
          const u = F((2 * x + 1) * px, 2);
          if (_inside(sh.kind, a, u, v)) owner[y * N + x] = geo.length - 1;
        }
      }
      sh.bbox = [bx0, by0, bx1, by1];
    }
    const drawn = order.map((i) => shapes[i]);
    const mats = _materials(data, g), lens = {};
    for (const k of Object.keys(mats)) lens[k] = mats[k].length;
    const bands = Math.min(TIER_BANDS[N], E_.bands);
    const dither = E_.dither && N >= 128;
    const shade = new Int32Array(N * N);
    for (let y = 0; y < N; y++) {
      const v = F((2 * y + 1) * px, 2);
      for (let x = 0; x < N; x++) {
        const o = owner[y * N + x];
        if (o < 0) continue;
        const sh = drawn[o];
        const [bx0, by0, bx1, by1] = sh.bbox;
        const hwid = Math.max(1, F(bx1 - bx0, 2)), hhei = Math.max(1, F(by1 - by0, 2));
        const u = F((2 * x + 1) * px, 2);
        const nx = Math.max(-1024, Math.min(1024, F((u - F(bx0 + bx1, 2)) * 1024, hwid)));
        const ny = Math.max(-1024, Math.min(1024, F((v - F(by0 + by1, 2)) * 1024, hhei)));
        const z = isqrt(Math.max(0, 1024 * 1024 - nx * nx - ny * ny));
        const light = F(-nx * 424 - ny * 566 + z * 707, 1024);
        shade[y * N + x] = shade_index(light, lens[sh.mat], bands, dither, x, y, sh.bias);
      }
    }
    const pixMat = Array.from(owner, (o) => (o >= 0 ? drawn[o].mat : ""));
    const depth = Array.from(owner, (o) => -o);
    const sigMats = Array.from(new Set(drawn.filter((sh) => vis.sigs.includes(sh.feat)).map((sh) => sh.mat))).sort(cmpStr);
    const spr = finish(data, g, N, N, N, era, pixMat, shade, depth, !!opts.rim, sigMats);
    const feats = Array.from(new Set(Array.from(owner).filter((o) => o >= 0).map((o) => drawn[o].feat))).sort(cmpStr);
    const out = { sprite: spr, features: feats };
    if (opts.want_map) {
      out.matmap = pixMat;
      out.featmap = Array.from(owner, (o) => (o >= 0 ? drawn[o].feat : ""));
    }
    return out;
  }
  function _eraReduce(spr, cap, reserveOutline, heavy) {
    heavy = heavy || new Set();
    const counts = new Map();
    for (const i of spr.px) if (i) counts.set(i, (counts.get(i) || 0) + 1);
    const keep = Array.from(counts.keys()).sort((a, b) => a - b);
    const locked = new Set();
    if (reserveOutline && keep.length) {
      const lum = (i) => 3 * spr.palette[i][0] + 6 * spr.palette[i][1] + spr.palette[i][2];
      let best = keep[0];
      for (const i of keep) if (lum(i) < lum(best)) best = i;
      locked.add(best);
    }
    const remap = new Map(keep.map((i) => [i, i]));
    while (keep.length > cap) {
      let best = null;
      for (let ai = 0; ai < keep.length; ai++) for (let bi = ai + 1; bi < keep.length; bi++) {
        const a = keep[ai], b = keep[bi];
        if (locked.has(a) && locked.has(b)) continue;
        const ca = spr.palette[a], cb = spr.palette[b];
        const d = 2 * (ca[0] - cb[0]) ** 2 + 4 * (ca[1] - cb[1]) ** 2 + 3 * (ca[2] - cb[2]) ** 2;
        const cost = d * Math.min(counts.get(a), counts.get(b)) * (heavy.has(a) || heavy.has(b) ? 8 : 1);
        if (best === null || cost < best[0]) best = [cost, a, b];
      }
      const [, a, b] = best;
      let win, lose;
      if (locked.has(a) || (!locked.has(b) && counts.get(a) >= counts.get(b))) { win = a; lose = b; } else { win = b; lose = a; }
      counts.set(win, counts.get(win) + counts.get(lose));
      counts.delete(lose);
      keep.splice(keep.indexOf(lose), 1);
      for (const [k, v] of remap) if (v === lose) remap.set(k, win);
    }
    for (let p = 0; p < spr.px.length; p++) { const i = spr.px[p]; if (i) spr.px[p] = remap.get(i); }
  }

  // ---------------------------------------------------------------- public rig API
  const POSES = {
    idle: [{}, { bob: 1 }, { bob: 1, blink: 1 }, {}],
    walk: [{ lift_l: 2, swing: 1 }, { bob: 1 }, { lift_r: 2, swing: -1 }, { bob: 1 }],
  };
  const STREAMS = ["g/body", "g/face", "g/hair", "g/outfit", "g/headwear", "g/items", "g/accessories"];
  // a team (clan colours) keeps the role's own hash: withTeam stores it, unlisted, in __hash
  const hashOf = (data) => data.__hash || PG.typeHash(data);
  const streamsFor = (data, seed, overrides) => new PG.Streams(PG.masterSeed(hashOf(data), seed), overrides);
  function rigFrames(data, seed, overrides, tier, era, anim = "idle") {
    const g = genome(data, streamsFor(data, seed, overrides));
    const t = tier || get(data, "tier", 64);
    return POSES[anim].map((p) => render(data, g, t, { era, pose: p }).sprite);
  }
  function chain(data, seed, tiers = TIERS, eras = null, overrides = null) {
    const g = genome(data, streamsFor(data, seed, overrides));
    return { genome: g, tiers: tiers.map((t) => {
      const era = get(eras || DEFAULT_CHAIN, t, "hd");
      const r = render(data, g, t, { era });
      return { tier: t, era, sprite: r.sprite, features: r.features, colors: r.sprite.usedColors() };
    }) };
  }
  const LEG_FEATS = ["legs", "feet", "bottom"];
  const legsVisible = (g) => !["robe", "dress", "cloak"].includes(g.top) && g.bottom !== "skirt" && g.back !== "cape";
  function legCount(featmap, N) {
    const rows = [];
    for (let y = 0; y < N; y++) { for (let x = 0; x < N; x++) if (LEG_FEATS.includes(featmap[y * N + x])) { rows.push(y); break; } }
    if (!rows.length) return 0;
    const band = rows.length >= 3 ? rows.slice(-3, -1) : rows;
    let best = 0;
    for (const y of band) {
      let runs = 0, inside = false, hasLeg = false;
      for (let x = 0; x <= N; x++) {
        const f = x < N ? featmap[y * N + x] : "";
        if (f !== "") { hasLeg = hasLeg || LEG_FEATS.includes(f); inside = true; }
        else { if (inside && hasLeg) runs += 1; inside = false; hasLeg = false; }
      }
      best = Math.max(best, runs);
    }
    return best;
  }
  function legsCheck(data, g, tier) {
    const alone = legCount(render(data, g, tier, { want_map: true, only_feats: ["legs", "feet"] }).featmap, tier);
    const shown = legsVisible(g) ? legCount(render(data, g, tier, { want_map: true }).featmap, tier) : null;
    return { tier, alone, shown, ok: alone === 2 && (shown === null || (shown >= 1 && shown <= 2)) };
  }
  function ladder() { return Object.keys(LOD).sort((a, b) => LOD[a] - LOD[b] || cmpStr(a, b)).map((k) => [k, LOD[k]]); }

  // ---------------------------------------------------------------- type composition (mirror typefile.compose)
  function merge(base, over) {
    const out = Object.assign({}, base);
    for (const [k, v] of Object.entries(over)) {
      if (k.endsWith("_add") && Array.isArray(v)) { const key = k.slice(0, -4); out[key] = (out[key] || []).concat(v); continue; }
      if (v && typeof v === "object" && !Array.isArray(v) && out[k] && typeof out[k] === "object" && !Array.isArray(out[k])) out[k] = merge(out[k], v);
      else out[k] = v;
    }
    return out;
  }
  function compose(baseData, overlayOwn, overlayId) {
    const own = Object.assign({}, overlayOwn);
    for (const k of ["schema", "id", "tag", "extends", "generator", "license", "role"]) delete own[k];
    const data = merge(JSON.parse(JSON.stringify(baseData)), own);
    data.id = baseData.id + "@" + overlayId.split(".").pop();
    return data;
  }

  // ---------------------------------------------------------------- scene composer (mirror gen/scene.py)
  let resolve = () => { throw new Error("no type resolver set"); };
  function setResolver(fn) { resolve = fn; }
  function sceneIdentity(data) {
    const refs = Array.from(new Set(data.crowd.flatMap((d) => d.roles))).sort(cmpStr);
    const parts = [PG.typeHash(data)].concat(refs.map((r) => PG.typeHash(resolve(r))));
    return PG.hex(PG.sha256(new TextEncoder().encode(parts.join(""))));
  }
  function colorIndex(spr, c) {
    if (c[3] === 0) return 0;
    for (let i = 0; i < spr.palette.length; i++) { const p = spr.palette[i]; if (p[0] === c[0] && p[1] === c[1] && p[2] === c[2] && p[3] === c[3]) return i; }
    spr.palette.push(c.slice());
    if (spr.palette.length > 256) throw new Error("sprite exceeds 256 colours");
    return spr.palette.length - 1;
  }
  function blit(dst, src, ox, oy) {
    const remap = src.palette.map((c, i) => (i ? colorIndex(dst, c) : 0));
    for (let y = 0; y < src.h; y++) for (let x = 0; x < src.w; x++) { const i = src.px[y * src.w + x]; if (i) dst.set(ox + x, oy + y, remap[i]); }
  }
  class Canvas {
    constructor(w, h) { this.w = w; this.h = h; this.spr = new PG.Sprite(w, h, [[0, 0, 0, 0]]); this.ramps = {}; }
    ramp(name, colors) { if (!(name in this.ramps)) { this.ramps[name] = this.spr.palette.length; for (const c of colors) this.spr.palette.push(PG.hexToRgba(c)); } return this.ramps[name]; }
    put(x, y, i) { if (x >= 0 && x < this.w && y >= 0 && y < this.h) this.spr.px[y * this.w + x] = i; }
    rect(x0, y0, x1, y1, i) { for (let y = Math.max(0, y0); y < Math.min(this.h, y1); y++) for (let x = Math.max(0, x0); x < Math.min(this.w, x1); x++) this.spr.px[y * this.w + x] = i; }
    ellipse(cx, cy, rx, ry, i) {
      for (let y = Math.max(0, cy - ry); y < Math.min(this.h, cy + ry + 1); y++) for (let x = Math.max(0, cx - rx); x < Math.min(this.w, cx + rx + 1); x++) {
        const dx = x - cx, dy = y - cy;
        if (dx * dx * ry * ry + dy * dy * rx * rx <= rx * rx * ry * ry) this.spr.px[y * this.w + x] = i;
      }
    }
    tri(x0, y0, x1, y1, x2, y2, i) {
      for (let y = Math.max(0, Math.min(y0, y1, y2)); y < Math.min(this.h, Math.max(y0, y1, y2) + 1); y++)
        for (let x = Math.max(0, Math.min(x0, x1, x2)); x < Math.min(this.w, Math.max(x0, x1, x2) + 1); x++) {
          const d0 = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0);
          const d1 = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1);
          const d2 = (x0 - x2) * (y - y2) - (y0 - y2) * (x - x2);
          if ((d0 >= 0 && d1 >= 0 && d2 >= 0) || (d0 <= 0 && d1 <= 0 && d2 <= 0)) this.spr.px[y * this.w + x] = i;
        }
    }
  }
  const imulU = (a, b) => Math.imul(a, b) >>> 0;
  const PROP_LOD = { door: 14, planks: 20, window_frame: 20, shingles: 32, scallops: 60, crates: 60 };
  function hutDetail(cv, px_, py, hw, hh, wd, nwd, rf, nrf) {
    if (hw >= PROP_LOD.planks) for (let yy = py - hh + 2; yy < py; yy += 3) cv.rect(px_ - F(hw, 2) + 1, yy, px_ + F(hw, 2) - 1, yy + 1, wd + Math.max(0, nwd - 4));
    if (hw >= PROP_LOD.window_frame) {
      const y0 = py - F(hh * 6, 10), y1 = py - F(hh * 2, 10);
      cv.rect(px_ - 2, y0 - 1, px_ + 3, y0, wd); cv.rect(px_ - 2, y1, px_ + 3, y1 + 1, wd);
      cv.rect(px_ - 2, y0, px_ - 1, y1, wd); cv.rect(px_ + 2, y0, px_ + 3, y1, wd);
    }
    if (hw >= PROP_LOD.door) { const dx = px_ + F(hw, 4); cv.rect(dx, py - F(hh * 55, 100), dx + Math.max(2, F(hw, 6)), py, wd + 1); }
    if (hw >= PROP_LOD.shingles) {
      const top = py - hh - F(hh * 7, 10);
      for (let yy = top + 3; yy < py - hh; yy += 3) {
        const half = F((yy - top) * F(hw * 7, 10), Math.max(1, F(hh * 7, 10)));
        for (let x = px_ - half + 1; x < px_ + half; x++) if (MOD(x + yy, 4) === 0) cv.put(x, yy, rf + Math.max(0, nrf - 4));
      }
    }
  }
  function stallDetail(cv, sx, sy, sw, H, aw, wd) {
    if (sw >= PROP_LOD.scallops) { const yb = sy - F(H, 5) + F(H, 40); for (let x = sx - 2; x < sx + sw + 2; x++) if (MOD(x - sx, 4) < 2) cv.put(x, yb, aw + 1); }
    if (sw >= PROP_LOD.crates) for (let k = 0; k < F(sw, 12); k++) { const cx = sx + 3 + k * 12; cv.rect(cx, sy - 5, cx + 5, sy - 1, wd + 2); cv.rect(cx, sy - 5, cx + 5, sy - 4, wd + 3); }
  }
  function sceneFrames(d, seed, overrides, onCrowd, population) {
    const [W, H] = d.size;
    const S = new PG.Streams(PG.masterSeed(sceneIdentity(d), seed), overrides);
    const P = d.palette, cv = new Canvas(W, H);
    const sky = cv.ramp("sky", P.sky), n = P.sky.length;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const band = F(y * (n - 1) * 16, Math.max(1, F(H * 6, 10)));
      const b = Math.min(n - 1, F(band, 16)), f = MOD(band, 16);
      const idx = f > BAYER4[y % 4][x % 4] && b + 1 <= n - 1 ? b + 1 : b;
      cv.spr.px[y * W + x] = sky + Math.min(n - 1, idx);
    }
    const cl = cv.ramp("cloud", P.cloud);
    let r = S.rng("clouds");
    for (let c = 0; c < get(d, "clouds", 4); c++) {
      const cx = r.below(W), cy = F(H, 20) + r.below(F(H, 5));
      for (let k = 0; k < 4; k++) cv.ellipse(cx + F((k - 2) * W, 40), cy + F((k % 2) * H, 60), F(W, 30) + r.below(F(W, 40) + 1), F(H, 40) + 1, cl + (k % 2 ? P.cloud.length - 1 : P.cloud.length - 2));
    }
    [[42, 14, "cliff_far"], [56, 12, "cliff"]].forEach(([base, amp, mat], li) => {
      const o = cv.ramp(mat, P[mat]), m = P[mat].length;
      const seedL = S.rng("ridge/" + li).next();
      for (let x = 0; x < W; x++) {
        const top = F(H * base, 100) - PG.noise1d(seedL, x, [F(W, 5) + 1, F(W, 16) + 2], [F(H * amp, 100), F(H * amp, 300)]);
        for (let y = Math.max(0, top); y < H; y++) {
          const depth = y - top;
          const speck = PG.hash32((seedL ^ imulU(x, 0x9e3779b1) ^ imulU(y, 0x85ebca6b)) >>> 0) % 9 === 0 ? 1 : 0;
          const sh = depth < 2 ? m - 1 : Math.max(0, m - 2 - F(depth * (m - 1), Math.max(1, H - top)) - speck);
          cv.spr.px[y * W + x] = o + sh;
        }
      }
    });
    const wa = cv.ramp("water", P.water), nw = P.water.length;
    const rw = S.rng("falls"), nf = get(d, "waterfalls", 3);
    for (let i = 0; i < nf; i++) {
      const fx = F(W * (15 + F(i * 70, Math.max(1, nf))), 100) + rw.below(F(W, 12));
      const fw = Math.max(2, F(W, 80) + rw.below(F(W, 90) + 1));
      const ftop = F(H * (30 + rw.below(14)), 100);
      for (let y = ftop; y < F(H * 74, 100); y++) for (let x = fx; x < fx + fw; x++) {
        const streak = (y * 3 + x * 7 + PG.hash32(x * 131 + i)) % 11;
        cv.put(x, y, wa + (streak < 3 ? nw - 1 : streak < 7 ? nw - 2 : nw - 3));
      }
      cv.ellipse(fx + F(fw, 2), F(H * 74, 100), fw * 2, Math.max(1, F(H, 60)), wa + nw - 1);
    }
    const lf = cv.ramp("leaf", P.leaf), nl = P.leaf.length, tr = cv.ramp("trunk", P.trunk);
    const rt = S.rng("trees");
    for (let i = 0; i < get(d, "trees", 10); i++) {
      const tx = rt.below(W), ty = F(H * (38 + rt.below(20)), 100);
      cv.rect(tx - 1, ty, tx + 1, ty + F(H, 8), tr + 1);
      for (let k = 0; k < 5; k++) {
        const rr = F(W, 40) + rt.below(F(W, 50) + 1);
        cv.ellipse(tx + F((k - 2) * rr, 2), ty - F((k % 3) * rr, 3), rr, F(rr * 3, 4), lf + Math.max(0, nl - 1 - (k % 3)));
      }
    }
    const wd = cv.ramp("wood", P.wood), nwd = P.wood.length, rf = cv.ramp("roof", P.roof), gl = cv.ramp("glow", P.glow), ng = P.glow.length;
    const rp = S.rng("platforms"), plats = [], nh = get(d, "huts", 5);
    for (let i = 0; i < nh; i++) {
      const px_ = F(W * (8 + F(i * 84, Math.max(1, nh))), 100) + rp.below(F(W, 20));
      const py = F(H * (40 + rp.below(22)), 100);
      const pw = F(W, 12) + rp.below(F(W, 16));
      plats.push([px_, py, pw]);
      cv.rect(px_ - F(pw, 2), py, px_ + F(pw, 2), py + 2, wd + nwd - 2);
      for (const sx of [px_ - F(pw, 2) + 1, px_ + F(pw, 2) - 2]) cv.rect(sx, py + 2, sx + 1, py + F(H, 7), wd + 1);
      const hw = F(pw * 6, 10), hh = F(H, 14) + rp.below(F(H, 30));
      cv.rect(px_ - F(hw, 2), py - hh, px_ + F(hw, 2), py, wd + nwd - 3);
      cv.tri(px_ - F(hw * 7, 10), py - hh, px_ + F(hw * 7, 10), py - hh, px_, py - hh - F(hh * 7, 10), rf + P.roof.length - 2);
      cv.tri(px_ - F(hw * 7, 10), py - hh, px_, py - hh, px_, py - hh - F(hh * 7, 10), rf + P.roof.length - 3);
      cv.rect(px_ - 1, py - F(hh * 6, 10), px_ + 2, py - F(hh * 2, 10), gl + ng - 2);
      hutDetail(cv, px_, py, hw, hh, wd, nwd, rf, P.roof.length);
      const lx = px_ + F(pw, 2) - 1;
      cv.put(lx, py - 3, wd);
      cv.ellipse(lx, py - 1, 1, 1, gl + ng - 1);
    }
    for (let p = 0; p + 1 < plats.length; p++) {
      const a = plats[p], b = plats[p + 1];
      if (Math.abs(a[1] - b[1]) < F(H, 6)) {
        const x0 = a[0] + F(a[2], 2), x1 = b[0] - F(b[2], 2);
        for (let x = x0; x < x1; x++) {
          const t = F((x - x0) * 1024, Math.max(1, x1 - x0));
          const sag = F(t * (1024 - t) * (F(H, 40) + 1), 1024 * 256);
          const y = a[1] + F((b[1] - a[1]) * t, 1024) + sag;
          cv.put(x, y, wd + nwd - 2);
          cv.put(x, y + 1, wd + 1);
          if (MOD(x, 4) === 0) cv.put(x, y - 1, wd + 2);
        }
      }
    }
    for (let y = F(H * 74, 100); y < F(H * 82, 100); y++) for (let x = 0; x < W; x++) {
      const band = (x + y * 2) % 13 === 0 ? 1 : 0;
      cv.spr.px[y * W + x] = wa + Math.max(0, nw - 3 + band - F((y - F(H * 74, 100)) * 2, Math.max(1, F(H * 8, 100))));
    }
    const gd = cv.ramp("ground", P.ground), ngd = P.ground.length;
    for (let y = F(H * 82, 100); y < H; y++) for (let x = 0; x < W; x++) {
      const h = PG.hash32(((x * 7919) ^ (y * 104729)) >>> 0) % 23;
      cv.spr.px[y * W + x] = gd + (y === F(H * 82, 100) ? ngd - 1 : h === 0 ? ngd - 2 : h === 1 ? 1 : ngd - 3);
    }
    const cl2 = P.awnings.map((c, i) => cv.ramp("awning" + i, c));
    const rs = S.rng("stalls"), ns = get(d, "stalls", 3);
    for (let i = 0; i < ns; i++) {
      const sx = F(W * (6 + F(i * 88, Math.max(1, ns))), 100) + rs.below(F(W, 20));
      const sw = F(W, 8) + rs.below(F(W, 20));
      const sy = F(H * 80, 100);
      const aw = cl2[rs.below(cl2.length)];
      cv.rect(sx, sy - F(H, 5), sx + 2, sy + F(H, 12), wd + 1);
      cv.rect(sx + sw - 2, sy - F(H, 5), sx + sw, sy + F(H, 12), wd + 1);
      for (let x = sx - 2; x < sx + sw + 2; x++) for (let y = sy - F(H, 5) - F(H, 30); y < sy - F(H, 5) + F(H, 40); y++)
        cv.put(x, y, aw + (MOD(F(x - sx, Math.max(2, F(W, 64))), 2) ? 3 : 1));
      cv.rect(sx, sy, sx + sw, sy + F(H, 20), wd + nwd - 2);
      for (let k = 0; k < F(sw, 3); k++) {
        cv.put(sx + 1 + k * 3, sy - 1, cl2[(k + i) % cl2.length] + 3);
        cv.put(sx + 2 + k * 3, sy - 1, gl + ng - 2);
      }
      cv.ellipse(sx + F(sw, 2), sy - F(H, 5) + F(H, 20), 1, 2, gl + ng - 1);
      stallDetail(cv, sx, sy, sw, H, aw, wd);
    }
    for (const band of d.crowd) {
      const rc = S.rng("crowd/" + band.name), tier = band.tier;
      const yLo = F(H * band.y[0], 100), yHi = F(H * band.y[1], 100);
      const placed = [];
      let pool = [];
      const people = population ? population.filter((p) => p.band === band.name) : null;
      for (let k = 0; k < (people ? people.length : band.count); k++) {
        let role, cdata, cseed, over = null;
        if (!people) {
          if (!pool.length) pool = band.roles.slice();
          role = pool.splice(rc.below(pool.length), 1)[0];
          cdata = resolve(role);
          cseed = rc.next();
        } else {
          const who = people[k];
          role = who.role;
          cdata = who.sub ? composeId(who.role, who.sub) : resolve(who.role);
          if (who.team) cdata = withTeam(cdata, who.team);
          cseed = who.seed;
          over = who.overrides || null;
        }
        const g = genome(cdata, streamsFor(cdata, cseed, over));
        const spr = render(cdata, g, tier, { era: band.era }).sprite;
        let x, y;
        if (band.on === "platforms" && plats.length) {
          const pl = plats[rc.below(plats.length)];
          x = pl[0] - F(pl[2], 2) + rc.below(Math.max(1, pl[2])) - F(tier, 2);
          y = pl[1] - tier + F(tier, 16);
        } else {
          x = rc.below(Math.max(1, W - F(tier, 2))) - F(tier, 4);
          y = yLo + rc.below(Math.max(1, yHi - yLo + 1)) - tier;
        }
        placed.push([y, x, spr, role, cseed, people ? people[k] : null]);
      }
      placed.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      for (const [y, x, spr, role, cseed, who] of placed) {
        blit(cv.spr, spr, x, y);
        if (onCrowd) onCrowd({ role, seed: cseed, tier, x, y, band: band.name, who });
      }
    }
    return [cv.spr];
  }


  // ---------------------------------------------------------------- names and families (mirror rng.seed_from_name, brood.family)
  function seedFromName(name) {
    const b = PG.sha256(new TextEncoder().encode("name:" + name.trim().split(/\s+/).join(" ").toLowerCase()));
    let n = 0n;
    for (let i = 7; i >= 0; i--) n = (n << 8n) | BigInt(b[i]);
    return n.toString();
  }
  function lineage(data, a, b, child) {
    const h = PG.typeHash(data);
    const C = new PG.Streams(PG.masterSeed(h, child)), PA = new PG.Streams(PG.masterSeed(h, a)), PB = new PG.Streams(PG.masterSeed(h, b));
    const pick = C.rng("brood/pick"), overrides = {}, inherited = {};
    for (const path of PG.streamPaths(data)) {
      const r = pick.below(100);
      if (r < 10) { inherited[path] = "mutation"; continue; }
      const src = r % 2 === 0 ? PA : PB;
      overrides[path] = src.seed(path); inherited[path] = src === PA ? "A" : "B";
    }
    return { overrides, inherited };
  }
  function family(data, founders, seed = 0) {
    const [a, b, c, d] = founders.map(Number);
    const kid1 = seed * 2 + 1001, kid2 = seed * 2 + 1002, grand = seed + 2001;
    const l1 = lineage(data, a, b, kid1), l2 = lineage(data, c, d, kid2);
    const h = PG.typeHash(data);
    const ks = { 1: new PG.Streams(PG.masterSeed(h, kid1), l1.overrides), 2: new PG.Streams(PG.masterSeed(h, kid2), l2.overrides) };
    const pick = new PG.Streams(PG.masterSeed(h, grand)).rng("brood/pick");
    const gOver = {}, gRec = {};
    for (const path of PG.streamPaths(data)) {
      const r = pick.below(100);
      if (r < 10) { gRec[path] = "mutation"; continue; }
      const side = r % 2 === 0 ? 1 : 2;
      gOver[path] = ks[side].seed(path); gRec[path] = side === 1 ? "child 1" : "child 2";
    }
    return { founders: [a, b, c, d],
      children: [{ seed: kid1, parents: [a, b], inherited: l1.inherited, overrides: l1.overrides },
                 { seed: kid2, parents: [c, d], inherited: l2.inherited, overrides: l2.overrides }],
      grandchild: { seed: grand, parents: [kid1, kid2], inherited: gRec, overrides: gOver } };
  }


  // ---------------------------------------------------------------- teams and overlays by id
  let teamTable = {}, ownTable = {};
  function setTables(teams, owns) { teamTable = teams || {}; ownTable = owns || {}; }
  function composeId(roleId, subId) { return compose(resolve(roleId), ownTable[subId], subId); }
  function withTeam(data, team) {
    const spec = typeof team === "string" ? teamTable[team] : team;
    if (!spec) throw new Error("unknown team " + team);
    const base = hashOf(data);
    const out = JSON.parse(JSON.stringify(data));
    const cloth = out.palette.cloth;
    const t = { name: spec.name, label: spec.label || spec.name };
    for (const k of ["a", "b"]) {
      let v = spec[k];
      if (Array.isArray(v)) { const key = "team_" + t.name + "_" + k; cloth[key] = v; v = key; }
      t[k] = v;
    }
    out.team = t;
    Object.defineProperty(out, "__hash", { value: base, enumerable: false });
    return out;
  }

  // ---------------------------------------------------------------- views (rig3d)
  const VIEWS = { front: [0, 0], back: [180, 0], side_left: [90, 0], side_right: [270, 0], iso_sw: [45, 30], iso_se: [315, 30],
    iso_nw: [135, 30], iso_ne: [225, 30], top: [0, 90], three_quarter: [0, 45] };
  const gridCache = new Map();
  function model(data, g, tier, pose, extent) {
    extent = extent || D;
    const vis = visibleShapes(data, g, F(tier * D, extent), pose, null, null, null);
    const [solids, decals] = lift(vis.shapes, g, F(extent, tier), pose || {});
    return { solids, decals, sigs: vis.sigs };
  }
  function gridFor(solids, n, extent) {
    const key = n + ":" + extent + ":" + JSON.stringify(solids.map((s) => [s.k, s.a, s.a2, s.layer, s.idx]));
    let hit = gridCache.get(key);
    if (!hit) {
      if (gridCache.size > 24) gridCache.clear();
      const grid = voxelize(solids, n, extent);
      hit = { grid, box: occupied_box(grid, n) };
      gridCache.set(key, hit);
    }
    return hit;
  }
  function renderView(data, g, tier, o = {}) {
    const extent = o.extent || D;
    const base = VIEWS[o.view || "front"];
    const yaw = o.yaw === undefined || o.yaw === null ? base[0] : o.yaw;
    const pitch = o.pitch === undefined || o.pitch === null ? base[1] : o.pitch;
    const era = o.era || get(DEFAULT_CHAIN, tier, "hd");
    let solids = o.solids, decals = o.decals, sigs = o.sigs || [];
    if (!solids) { const m = model(data, g, tier, o.pose, extent); solids = m.solids; decals = m.decals; sigs = m.sigs; }
    const { grid, box } = gridFor(solids, tier, extent);
    const [W, H, hit, vox, dist] = trace(grid, tier, extent, yaw, pitch, box);
    const E_ = ERAS[era], mats = _materials(data, g), lens = {};
    for (const k of Object.keys(mats)) lens[k] = mats[k].length;
    const [pixMat, shade] = paint(solids, decals, hit, vox, dist, W, H, tier, extent, yaw, pitch, Math.min(TIER_BANDS[tier], E_.bands), E_.dither && tier >= 128, lens);
    const sigMats = Array.from(new Set(solids.filter((s) => sigs.includes(s.feat)).map((s) => s.mat))).sort(cmpStr);
    const sprite = finish(data, g, W, H, tier, era, pixMat, shade, dist, !!o.rim, sigMats);
    return { sprite, pixMat, featmap: Array.from(hit, (m) => (m ? solids[m - 1].feat : "")) };
  }
  const VIEW_POSES = { idle: POSES.idle, walk_side: [{ stride: 2 }, { bob: 1 }, { stride: -2 }, { bob: 1 }] };

  // ---------------------------------------------------------------- beasts and riders (beast.py)
  function beastGenome(data, S) {
    const bd = get(data, "beast", {});
    const b = S.rng("b/body");
    const g = { kind: get(bd, "kind", "boar") };
    g.length = _rngRange(b, get(bd, "length", [820, 960]));
    g.height = _rngRange(b, get(bd, "height", [430, 520]));
    g.girth = _rngRange(b, get(bd, "girth", [150, 190]));
    const h = S.rng("b/head");
    g.head = _rngRange(h, get(bd, "head", [120, 150]));
    g.snout = _rngRange(h, get(bd, "snout", [60, 100]));
    g.ear = _rngRange(h, get(bd, "ear", [40, 70]));
    g.tail = _rngRange(h, get(bd, "tail", [60, 120]));
    g.tusks = h.chance(get(bd, "tusk_chance", 0)) ? 1 : 0;
    const c = S.rng("b/coat");
    g.hair_color = _pick(c, get(bd, "coat", ["brown"]), "brown");
    g.iris = _pick(c, get(bd, "iris", ["amber"]), "amber");
    const t = S.rng("b/tack");
    g.cloth_a = _pick(t, get(bd, "blanket", ["red"]), "red");
    g.cloth_b = "leather";
    g.saddle = t.chance(get(bd, "saddle_chance", 100)) ? 1 : 0;
    const team = get(data, "team", null);
    if (team) { g.cloth_a = team.a; g.team = team.name; }
    return g;
  }
  function beastRender(data, bg, tier, o = {}) {
    const solids = beast_solids(bg, F(EXT, tier), o.pose || {}, "");
    return renderView(data, bg, tier, Object.assign({ view: "side_right" }, o, { extent: EXT, solids, decals: [] }));
  }
  function mountedData(riderData, beastData, bg) {
    const data = JSON.parse(JSON.stringify(riderData));
    const m = _materials(beastData, bg);
    for (const k of Object.keys(m)) data.palette.materials["beast_" + k] = m[k];
    return data;
  }
  function mounted(riderData, g, beastData, bg, tier, o = {}) {
    const px = F(EXT, tier);
    const m = model(riderData, g, tier, o.pose, EXT);
    const [rider, rdecals] = seat_rider(m.solids, m.decals, bg, px);
    const both = beast_solids(bg, px, o.pose || {}, "beast_").concat(rider);
    both.sort((a, b) => a.layer - b.layer || (a.group === 0) - (b.group === 0) || a.idx - b.idx);
    return renderView(mountedData(riderData, beastData, bg), g, tier, Object.assign({ view: "side_right" }, o, { extent: EXT, solids: both, decals: rdecals, sigs: m.sigs }));
  }

  // ---------------------------------------------------------------- sheets: expressions, teams, zoom (cards.py)
  function zoomFrames(data, g, fromTier, toTier, steps) {
    const cache = {};
    const at = (t) => cache[t] || (cache[t] = render(data, g, t, {}).sprite);
    return zoom_plan(fromTier, toTier, steps).map(([size, a, b, w]) => {
      const out = new PG.Sprite(toTier, toTier, [[0, 0, 0, 0]]);
      const A = at(a), B = at(b);
      const ox = F(toTier - size, 2), oy = toTier - size;
      for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
        const src = w > BAYER4[y % 4][x % 4] ? B : A;
        const i = src.px[F(y * src.h, size) * src.w + F(x * src.w, size)];
        if (i) out.set(ox + x, oy + y, colorIndex(out, src.palette[i]));
      }
      return out;
    });
  }

  // ---------------------------------------------------------------- city (city.py)
  function parseNames(text) {
    const out = [];
    for (let line of text.split(/\r?\n/)) {
      line = line.split("#")[0].trim();
      if (!line) continue;
      let role = null, tag = null;
      const ci = line.indexOf(":");
      if (ci >= 0) { role = line.slice(ci + 1).trim(); line = line.slice(0, ci).trim(); }
      const m = line.match(/\((child|elder|adult)\)\s*$/);
      if (m) { tag = m[1]; line = line.slice(0, m.index).trim(); }
      const name = line.split(/\s+/).join(" ");
      const words = name.split(" ");
      out.push({ name, household: words.length > 1 ? words[words.length - 1] : name, role, tag });
    }
    return out;
  }
  const weighted = (rng, table) => { const keys = Object.keys(table).sort(cmpStr); return keys[rng.weighted(keys.map((k) => table[k]))]; };
  function cityHash(city) { return PG.hex(PG.sha256(new TextEncoder().encode(PG.canonical(city)))); }
  function citizenType(p) {
    let data = p.sub ? composeId(p.role, "boc.goblin.sub." + p.sub) : resolve(p.role);
    if (p.team) data = withTeam(data, p.team);
    return data;
  }
  function census(city, names) {
    const ch = cityHash(city), ns = get(city, "role_prefix", "boc.goblin.");
    const houses = {}, people = [];
    for (const n of names) {
      const seed = seedFromName(n.name);
      const S = new PG.Streams(PG.masterSeed(ch, seed));
      const house = houses[n.household] || (houses[n.household] = []);
      const H = new PG.Streams(PG.masterSeed(ch, seedFromName("house:" + n.household)));
      const grown = house.filter((p) => p.age_group !== "child");
      const tag = n.tag || (grown.length >= 2 ? "child" : "adult");
      let role;
      if (n.role) role = n.role;
      else if (tag === "child") role = weighted(S.rng("city/role"), get(city, "children", { child_boy: 1, child_girl: 1 }));
      else if (tag === "elder") role = weighted(S.rng("city/role"), get(city, "elders", { elder: 1 }));
      else role = weighted(S.rng("city/role"), city.census);
      const sub = weighted(H.rng("city/sub"), get(city, "subspecies", { common: 1 }));
      const clans = get(city, "clans", []);
      let team = clans.length ? clans[H.rng("city/clan").below(clans.length)] : null;
      for (const c of clans) if (c.toLowerCase() === n.household.toLowerCase()) team = c;
      const p = { name: n.name, seed, role: role.includes(".") ? role : ns + role, sub: sub === "common" ? null : sub, team,
        household: n.household, age_group: tag, parents: [], band: weighted(S.rng("city/band"), get(city, "bands", { far: 3, mid: 4, near: 1 })) };
      if (tag === "child" && grown.length >= 2) {
        const [pa, pb] = grown;
        p.parents = [pa.name, pb.name];
        const pick = S.rng("city/inherit"), over = {}, record = {};
        for (const path of ["g/body", "g/face", "g/hair"]) {
          const r = pick.below(100);
          if (r < 10) { record[path] = "mutation"; continue; }
          const src = r % 2 === 0 ? pa : pb;
          over[path] = streamsFor(citizenType(src), src.seed, src.overrides || null).seed(path);
          record[path] = src.name;
        }
        p.overrides = over;
        p.inherited = record;
      }
      house.push(p);
      people.push(p);
    }
    return people;
  }
  function citizenSprite(p, tier, era) {
    const data = citizenType(p);
    const g = genome(data, streamsFor(data, p.seed, p.overrides || null));
    return render(data, g, tier, { era }).sprite;
  }
  function cityVillage(city, people, seed, onCrowd) {
    const sc = resolve(city.scene);
    const cap = {};
    for (const b of sc.crowd) cap[b.name] = b.count;
    const shown = [];
    for (const p of people) {
      if ((cap[p.band] || 0) > 0) {
        cap[p.band] -= 1;
        shown.push({ role: p.role, seed: p.seed, band: p.band, overrides: p.overrides || null, sub: p.sub ? "boc.goblin.sub." + p.sub : null, team: p.team, name: p.name });
        p.outdoors = true;
      } else p.outdoors = false;
    }
    return sceneFrames(sc, seed, null, onCrowd, shown)[0];
  }

  PG.register("rig", (data, seed, overrides) => rigFrames(data, seed, overrides), () => STREAMS.slice());
  PG.register("scene", (data, seed, overrides) => sceneFrames(data, seed, overrides),
    (data) => ["clouds", "ridge/0", "ridge/1", "falls", "trees", "platforms", "stalls"].concat(data.crowd.map((b) => "crowd/" + b.name)));
  return { TIERS, LOD, ERAS, DEFAULT_CHAIN, EXPRESSIONS, POSES, genome, render, chain, rigFrames, streamsFor, legsCheck, legCount,
    ladder, compose, merge, setResolver, sceneFrames, sceneIdentity, seedFromName, lineage, family, F, MOD,
    VIEWS, VIEW_POSES, model, renderView, signature, zoomFrames, zoom_plan, setTables, withTeam, composeId,
    beastGenome, beastRender, mounted, EXT, parseNames, census, citizenSprite, cityVillage, cityHash, isin, camera, canvas_size };
})(PG);
if (typeof module !== "undefined") module.exports = PGRig;
