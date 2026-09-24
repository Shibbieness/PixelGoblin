/* PixelGoblin core — JavaScript port of the integer-only runtime generators.
   Built on PixelGoblin — © Shibbieness / M MAOU LLC · AGPL-3.0-or-later
   Line-for-line mirror of pixelgoblin/{rng,typefile,gen/*,tiles/autotile}.py.
   Build gate B13 checks this file against the Python goldens under node;
   the editor page embeds this exact text (tools/build_editor.py). */
const PG = (() => {
  "use strict";
  const M32 = 0xffffffff;
  const ENGINE_MAJOR = 0;

  // ---------------------------------------------------------------- sha256
  const K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]);
  function sha256(bytes) {
    const H = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
    const l = bytes.length, nb = ((l + 9 + 63) >> 6) << 6;
    const m = new Uint8Array(nb); m.set(bytes); m[l] = 0x80;
    const bits = l * 8;
    for (let i = 0; i < 8; i++) m[nb - 1 - i] = Math.floor(bits / Math.pow(2, 8 * i)) & 255;
    const w = new Uint32Array(64);
    for (let o = 0; o < nb; o += 64) {
      for (let i = 0; i < 16; i++) w[i] = (m[o + 4 * i] << 24) | (m[o + 4 * i + 1] << 16) | (m[o + 4 * i + 2] << 8) | m[o + 4 * i + 3];
      for (let i = 16; i < 64; i++) {
        const a = w[i - 15], b = w[i - 2];
        const s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
        const s1 = ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = H;
      for (let i = 0; i < 64; i++) {
        const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
        const ch = (e & f) ^ (~e & g);
        const t1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
        const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
        const mj = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (S0 + mj) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] += a; H[1] += b; H[2] += c; H[3] += d; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
    }
    const out = new Uint8Array(32);
    for (let i = 0; i < 8; i++) { out[4 * i] = H[i] >>> 24; out[4 * i + 1] = (H[i] >>> 16) & 255; out[4 * i + 2] = (H[i] >>> 8) & 255; out[4 * i + 3] = H[i] & 255; }
    return out;
  }
  const hex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  const unhex = (s) => Uint8Array.from(s.match(/../g).map((x) => parseInt(x, 16)));
  const utf8 = (s) => new TextEncoder().encode(s);
  const cat = (...arrs) => { const n = arrs.reduce((a, b) => a + b.length, 0); const o = new Uint8Array(n); let p = 0; for (const a of arrs) { o.set(a, p); p += a.length; } return o; };

  // ---------------------------------------------------------------- canonical JSON
  function canonical(v) {
    if (v === null || typeof v !== "object") return JSON.stringify(v);
    if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
    const ks = Object.keys(v).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    return "{" + ks.map((k) => JSON.stringify(k) + ":" + canonical(v[k])).join(",") + "}";
  }
  const typeHash = (data) => hex(sha256(utf8(canonical(data))));

  // ---------------------------------------------------------------- rng
  const rotl = (x, k) => ((x << k) | (x >>> (32 - k))) >>> 0;
  function hash32(x) {
    x >>>= 0;
    x ^= x >>> 16; x = Math.imul(x, 0x7feb352d) >>> 0;
    x ^= x >>> 15; x = Math.imul(x, 0x846ca68b) >>> 0;
    x ^= x >>> 16;
    return x >>> 0;
  }
  class Rng {
    constructor(seed16) {
      const dv = new DataView(seed16.buffer, seed16.byteOffset, 16);
      this.s = [dv.getUint32(0, true), dv.getUint32(4, true), dv.getUint32(8, true), dv.getUint32(12, true)];
      if (!(this.s[0] | this.s[1] | this.s[2] | this.s[3])) this.s[0] = 1;
    }
    next() {
      let [s0, s1, s2, s3] = this.s;
      const result = Math.imul(rotl(Math.imul(s1, 5) >>> 0, 7), 9) >>> 0;
      const t = (s1 << 9) >>> 0;
      s2 = (s2 ^ s0) >>> 0; s3 = (s3 ^ s1) >>> 0; s1 = (s1 ^ s2) >>> 0; s0 = (s0 ^ s3) >>> 0;
      s2 = (s2 ^ t) >>> 0; s3 = rotl(s3, 11);
      this.s = [s0, s1, s2, s3];
      return result;
    }
    below(n) {
      const limit = Math.floor(4294967296 / n) * n;
      for (;;) { const r = this.next(); if (r < limit) return r % n; }
    }
    range(lo, hi) { return lo + this.below(hi - lo + 1); }
    chance(p) { return this.below(100) < p; }
    weighted(ws) {
      const total = ws.reduce((a, b) => a + b, 0);
      let r = this.below(total);
      for (let i = 0; i < ws.length; i++) { if (r < ws[i]) return i; r -= ws[i]; }
      throw new Error("unreachable");
    }
  }
  const derive = (seed16, path) => sha256(cat(seed16, utf8("/" + path))).slice(0, 16);
  function masterSeed(typeHashHex, userSeed, major = ENGINE_MAJOR) {
    let s = BigInt(userSeed);
    const sb = new Uint8Array(8);
    for (let i = 0; i < 8; i++) { sb[i] = Number(s & 255n); s >>= 8n; }
    return sha256(cat(utf8("PG"), unhex(typeHashHex), sb, Uint8Array.of(major & 255))).slice(0, 16);
  }
  class Streams {
    constructor(master, overrides) { this.master = master; this.overrides = overrides || {}; }
    seed(path) { return this.overrides[path] || derive(this.master, path); }
    rng(path) { return new Rng(this.seed(path)); }
  }

  // ---------------------------------------------------------------- sprite
  const T = [0, 0, 0, 0];
  function hexToRgba(s) {
    s = s.trim().replace(/^#/, "");
    if (s.length === 6) s += "ff";
    return [0, 2, 4, 6].map((i) => parseInt(s.slice(i, i + 2), 16));
  }
  class Sprite {
    constructor(w, h, palette) { this.w = w; this.h = h; this.palette = palette || [T]; this.px = new Uint8Array(w * h); }
    get(x, y) { return x >= 0 && x < this.w && y >= 0 && y < this.h ? this.px[y * this.w + x] : 0; }
    set(x, y, i) { if (x >= 0 && x < this.w && y >= 0 && y < this.h) this.px[y * this.w + x] = i; }
    copy() { const s = new Sprite(this.w, this.h, this.palette.map((c) => c.slice())); s.px.set(this.px); return s; }
    pixelHash() {
      const head = new Uint8Array(12), dv = new DataView(head.buffer);
      dv.setUint32(0, this.w, true); dv.setUint32(4, this.h, true); dv.setUint32(8, this.palette.length, true);
      return hex(sha256(cat(head, Uint8Array.from(this.palette.flat()), this.px)));
    }
    usedColors() { return new Set(Array.from(this.px).filter((i) => i)).size; }
  }

  // ---------------------------------------------------------------- mask generator
  const get = (o, k, d) => (o && o[k] !== undefined ? o[k] : d);
  function touchBody(cells, x, y, W, H) {
    return (y > 0 && cells[y - 1][x] === 1) || (x > 0 && cells[y][x - 1] === 1) ||
      (x < W - 1 && cells[y][x + 1] === 1) || (y < H - 1 && cells[y + 1][x] === 1);
  }
  const isBody = (cells, x, y, W, H) => x >= 0 && x < W && y >= 0 && y < H && cells[y][x] === 1;
  function buildCells(data, S) {
    const [W, H] = data.size, ramps = data.palette.ramps, names = ramps.map((r) => r.name);
    const mirror = !!get(data, "mirror", false);
    const cells = Array.from({ length: H }, () => new Array(W).fill(0));
    const rampof = Array.from({ length: H }, () => new Array(W).fill(-1));
    const layers = [["body", data.body]].concat((data.parts || []).map((p) => ["part/" + p.name, p]));
    for (const [path, L] of layers) {
      const rng = S.rng(path);
      if (path !== "body" && !rng.chance(L.chance)) continue;
      const sel = get(L, "ramp", "any");
      const ri = sel === "any" ? rng.weighted(ramps.map((r) => r.weight)) : names.indexOf(sel);
      const t = L.template, [ax, ay] = L.anchor, tw = t[0].length, fw = mirror ? tw * 2 : tw;
      for (let y = 0; y < t.length; y++) {
        for (let x = 0; x < tw; x++) {
          const c = t[y][x];
          if (c === ".") continue;
          let v;
          if (c === "#") v = 1;
          else if (c === "1") v = rng.below(2) === 0 ? 1 : 0;
          else v = rng.below(2) === 0 ? 1 : 2;
          if (v === 0) continue;
          const xs = mirror ? [x, fw - 1 - x] : [x];
          for (const xx of xs) {
            const X = ax + xx, Y = ay + y;
            if (v === 1) { cells[Y][X] = 1; rampof[Y][X] = ri; } else if (cells[Y][X] === 0) cells[Y][X] = 2;
          }
        }
      }
    }
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (cells[y][x] === 0 && touchBody(cells, x, y, W, H)) cells[y][x] = 3;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (cells[y][x] === 3) cells[y][x] = 2;
      else if (cells[y][x] === 2 && !touchBody(cells, x, y, W, H)) cells[y][x] = 0;
    }
    return [cells, rampof];
  }
  function squash(s) {
    const W = s.w, H = s.h, rows = [];
    for (let y = 0; y < H; y++) { for (let x = 0; x < W; x++) if (s.px[y * W + x]) { rows.push(y); break; } }
    if (rows.length < 3) return;
    const mid = Math.floor((rows[0] + rows[rows.length - 1]) / 2);
    for (let y = mid; y > 0; y--) s.px.copyWithin(y * W, (y - 1) * W, y * W);
    s.px.fill(0, 0, W);
  }
  function maskFrames(data, S) {
    const [W, H] = data.size, ramps = data.palette.ramps, mirror = !!get(data, "mirror", false);
    const [cells, rampof] = buildCells(data, S);
    const feats = get(data, "features", {});
    const offsets = [], pal = [T, hexToRgba(data.palette.outline), hexToRgba(get(feats, "eye_color", "#f4f4f4"))];
    for (const r of ramps) { offsets.push(pal.length); for (const c of r.colors) pal.push(hexToRgba(c)); }
    const bax = data.body.anchor[0], bfw = data.body.template[0].length * (mirror ? 2 : 1);
    const mx = (x) => 2 * bax + bfw - 1 - x;
    const tex = S.rng("shade").next();
    const spr = new Sprite(W, H, pal);
    const selout = get(data, "outline_style", "selout") === "selout";
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const c = cells[y][x];
      if (c === 1) {
        const cols = ramps[rampof[y][x]].colors, n = cols.length, mid = Math.floor((n - 1) / 2);
        let s;
        if (!isBody(cells, x, y - 1, W, H)) s = n - 1;
        else if (!isBody(cells, x, y + 1, W, H)) s = 0;
        else if (!isBody(cells, x - 1, y, W, H)) s = Math.min(n - 1, mid + 1);
        else if (!isBody(cells, x + 1, y, W, H)) s = Math.max(0, mid - 1);
        else {
          const xx = mirror ? Math.min(x, mx(x)) : x;
          const h = hash32((tex ^ (Math.imul(xx, 0x9e3779b1) >>> 0) ^ (Math.imul(y, 0x85ebca6b) >>> 0)) >>> 0);
          s = h % 8 === 0 ? Math.min(n - 1, mid + 1) : mid;
        }
        spr.px[y * W + x] = offsets[rampof[y][x]] + s;
      } else if (c === 2) {
        let idx = 1;
        if (selout) {
          for (const [dx, dy] of [[0, -1], [-1, 0], [1, 0], [0, 1]]) {
            if (isBody(cells, x + dx, y + dy, W, H)) { idx = offsets[rampof[y + dy][x + dx]]; break; }
          }
        }
        spr.px[y * W + x] = idx;
      }
    }
    const eyes = get(feats, "eyes", 0), eyePx = [];
    if (eyes) {
      const rng = S.rng("eyes");
      const rows = [];
      for (let y = 0; y < H; y++) if (cells[y].some((v) => v === 1)) rows.push(y);
      const top = rows[0], bot = rows[rows.length - 1];
      const [b0, b1] = get(feats, "eye_band", [0, 60]);
      const lo = top + Math.floor((bot - top) * b0 / 100), hi = top + Math.floor((bot - top) * b1 / 100);
      const cand = [];
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (cells[y][x] === 1 && lo <= y && y <= hi &&
          [[0, -1], [-1, 0], [1, 0], [0, 1]].every(([dx, dy]) => isBody(cells, x + dx, y + dy, W, H)) &&
          (!mirror || x < bax + Math.floor(bfw / 2))) cand.push([x, y]);
      }
      for (let e = 0; e < eyes; e++) {
        if (!cand.length) break;
        const [x, y] = cand.splice(rng.below(cand.length), 1)[0];
        eyePx.push([x, y]);
        if (mirror) eyePx.push([mx(x), y]);
      }
      for (const [x, y] of eyePx) spr.px[y * W + x] = 2;
    }
    const frames = [spr], n = get(get(data, "animation", {}), "frames", 1);
    for (let k = 1; k < n; k++) {
      const f = spr.copy();
      if (k % 2 === 1) squash(f);
      if (k === 2) for (const [x, y] of eyePx) if (f.px[y * W + x] === 2) f.px[y * W + x] = 1;
      frames.push(f);
    }
    return frames;
  }

  // ---------------------------------------------------------------- lsystem
  const DIRS = [[1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1]];
  function line(x0, y0, x1, y1) {
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    let err = dx + dy; const pts = [];
    for (;;) {
      pts.push([x0, y0]);
      if (x0 === x1 && y0 === y1) return pts;
      const e2 = 2 * err;
      if (e2 >= dy) { err += dy; x0 += sx; }
      if (e2 <= dx) { err += dx; y0 += sy; }
    }
  }
  function lsystemFrames(data, S) {
    const [W, H] = data.size;
    const grow = S.rng("grow");
    let s = data.axiom;
    for (let it = 0; it < data.iterations; it++) {
      let out = "";
      for (const ch of s) {
        if (Object.prototype.hasOwnProperty.call(data.rules, ch)) {
          const opts = data.rules[ch];
          out += opts.length > 1 ? opts[grow.weighted(opts.map((o) => o.weight))].to : opts[0].to;
        } else out += ch;
      }
      s = out;
    }
    const stepR = S.rng("step"), fruitR = S.rng("fruit");
    const [lo, hi] = data.step, rad = data.leaf_radius, tw = data.trunk_width;
    const cells = Array.from({ length: H }, () => new Array(W).fill(0));
    let x = Math.floor(W / 2), y = H - 2, d = 2, depth = 0;
    const stack = [];
    const put = (px, py, kind) => {
      if (px >= 1 && px < W - 1 && py >= 1 && py < H - 1) {
        if (kind === 1 || cells[py][px] === 0 || (kind === 3 && cells[py][px] === 2)) cells[py][px] = kind;
      }
    };
    const leaf = (cx, cy) => {
      const fruit = fruitR.chance(data.fruit_chance);
      for (let oy = -rad; oy <= rad; oy++) for (let ox = -rad; ox <= rad; ox++) if (Math.abs(ox) + Math.abs(oy) <= rad) put(cx + ox, cy + oy, 2);
      if (fruit) put(cx, cy + (rad ? 1 : 0), 3);
    };
    for (const ch of s) {
      if (ch === "F") {
        const n = stepR.range(lo, hi), [dx, dy] = DIRS[d], nx = x + dx * n, ny = y + dy * n;
        for (const [px, py] of line(x, y, nx, ny)) { put(px, py, 1); if (depth === 0 && tw === 2) put(px + 1, py, 1); }
        x = nx; y = ny;
      } else if (ch === "+") d = (d + 1) % 8;
      else if (ch === "-") d = (d + 7) % 8;
      else if (ch === "[") { stack.push([x, y, d, depth]); depth += 1; }
      else if (ch === "]") { leaf(x, y); if (stack.length) [x, y, d, depth] = stack.pop(); }
      else if (ch === "L") leaf(x, y);
    }
    const bark = data.palette.bark.map(hexToRgba), leafc = data.palette.leaf.map(hexToRgba);
    const pal = [T, hexToRgba(data.palette.outline), hexToRgba(data.palette.fruit)].concat(bark, leafc);
    const ob = 3, ol = 3 + bark.length, spr = new Sprite(W, H, pal);
    for (let yy = 0; yy < H; yy++) for (let xx = 0; xx < W; xx++) {
      const k = cells[yy][xx];
      if (k === 0) {
        const touch = [[0, -1], [-1, 0], [1, 0], [0, 1]].some(([a, b]) => xx + a >= 0 && xx + a < W && yy + b >= 0 && yy + b < H && cells[yy + b][xx + a]);
        if (touch) spr.px[yy * W + xx] = 1;
        continue;
      }
      if (k === 3) { spr.px[yy * W + xx] = 2; continue; }
      const [cols, off] = k === 1 ? [bark, ob] : [leafc, ol];
      const up = yy > 0 && cells[yy - 1][xx] === k, lf = xx > 0 && cells[yy][xx - 1] === k;
      const m = Math.floor((cols.length - 1) / 2);
      const sh = !up ? cols.length - 1 : (lf ? m : Math.max(0, m - 1));
      spr.px[yy * W + xx] = off + sh;
    }
    return [spr];
  }

  // ---------------------------------------------------------------- parallax
  const BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
  function lattice(seed, octave, i, amp) {
    if (amp === 0) return 0;
    const h = hash32((seed ^ (Math.imul(i, 0x9e3779b1) >>> 0) ^ (Math.imul(octave, 0x632be5ab) >>> 0)) >>> 0);
    return (h % (2 * amp + 1)) - amp;
  }
  function noise1d(seed, x, periods, amps) {
    let total = 0;
    for (let o = 0; o < periods.length; o++) {
      const p = periods[o], a = amps[o], i = Math.floor(x / p), t = x % p;
      const va = lattice(seed, o, i, a), vb = lattice(seed, o, i + 1, a);
      const s = Math.floor((t * t * (3 * p - 2 * t) * 1024) / (p * p * p));
      total += Math.floor((va * 1024 + (vb - va) * s) / 1024);
    }
    return total;
  }
  function band(depth, span, n, x, y) {
    const b16 = Math.floor(depth * (n - 1) * 16 / Math.max(1, span)), b = Math.floor(b16 / 16), f = b16 % 16;
    return f > BAYER4[y % 4][x % 4] && b + 1 <= n - 1 ? b + 1 : b;
  }
  function parallaxLayers(data, S) {
    const [W, H] = data.size, sky = data.palette.sky.map(hexToRgba);
    const pal = [T, hexToRgba(get(data.palette, "star", "#f4f4f4"))].concat(sky);
    const offs = [];
    for (const L of data.layers) { offs.push(pal.length); for (const c of L.colors) pal.push(hexToRgba(c)); }
    const comp = new Sprite(W, H, pal), n = sky.length;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) comp.px[y * W + x] = 2 + band(y, H - 1, n, x, y);
    const rng = S.rng("stars");
    for (let k = 0; k < get(data, "stars", 0); k++) { const x = rng.below(W), y = rng.below(Math.max(1, Math.floor(H * 2 / 5))); comp.px[y * W + x] = 1; }
    const out = [["composite", 0, comp]];
    data.layers.forEach((L, li) => {
      const lseed = S.rng("layer/" + L.name).next(), layer = new Sprite(W, H, pal);
      const baseY = Math.floor(H * L.base / 100), cols = L.colors.length;
      for (let x = 0; x < W; x++) {
        const top = baseY - noise1d(lseed, x, L.periods, L.amps);
        for (let y = Math.max(0, top); y < H; y++) {
          const depth = y - top, ci = depth === 0 ? cols - 1 : (cols - 1) - band(depth, H - top, cols, x, y);
          layer.px[y * W + x] = offs[li] + ci; comp.px[y * W + x] = offs[li] + ci;
        }
      }
      out.push([L.name, L.scroll, layer]);
    });
    return out;
  }

  // ---------------------------------------------------------------- autotile
  const [N, NE, E, SE, S_, SW, W_, NW] = [1, 2, 4, 8, 16, 32, 64, 128];
  const DIAG = [[NE, N, E], [SE, S_, E], [SW, S_, W_], [NW, N, W_]];
  const NEIGH = [[0, -1, N], [1, -1, NE], [1, 0, E], [1, 1, SE], [0, 1, S_], [-1, 1, SW], [-1, 0, W_], [-1, -1, NW]];
  const COLS = 8;
  function reduceMask(m) { for (const [d, a, b] of DIAG) if (!((m & a) && (m & b))) m &= ~d; return m & 255; }
  function blobMasks() { const s = new Set(); for (let m = 0; m < 256; m++) s.add(reduceMask(m)); return Array.from(s).sort((a, b) => a - b); }
  function indexTable() { const order = new Map(blobMasks().map((m, i) => [m, i])); const t = []; for (let m = 0; m < 256; m++) t.push(order.get(reduceMask(m))); return t; }
  function dist(mask, x, y, Tt) {
    const c = [];
    if (!(mask & N)) c.push([y, true]);
    if (!(mask & S_)) c.push([Tt - 1 - y, false]);
    if (!(mask & W_)) c.push([x, true]);
    if (!(mask & E)) c.push([Tt - 1 - x, false]);
    if ((mask & N) && (mask & E) && !(mask & NE)) c.push([Math.max(y, Tt - 1 - x), true]);
    if ((mask & N) && (mask & W_) && !(mask & NW)) c.push([Math.max(y, x), true]);
    if ((mask & S_) && (mask & E) && !(mask & SE)) c.push([Math.max(Tt - 1 - y, Tt - 1 - x), false]);
    if ((mask & S_) && (mask & W_) && !(mask & SW)) c.push([Math.max(Tt - 1 - y, x), false]);
    let best = 99, north = false;
    for (const [d, nf] of c) if (d < best) { best = d; north = nf; }
    return [best, north];
  }
  function buildTileset(data, S) {
    const Tt = data.tile, fill = data.palette.fill.map(hexToRgba);
    const pal = [T, hexToRgba(data.palette.outline), hexToRgba(data.palette.highlight)].concat(fill);
    const tex = S.rng("texture").next(), masks = blobMasks(), rows = Math.ceil(masks.length / COLS);
    const sheet = new Sprite(COLS * Tt, rows * Tt, pal), nf = fill.length, mid = 3 + Math.floor((nf - 1) / 2);
    masks.forEach((m, ti) => {
      const ox = (ti % COLS) * Tt, oy = Math.floor(ti / COLS) * Tt;
      for (let y = 0; y < Tt; y++) for (let x = 0; x < Tt; x++) {
        const [d, north] = dist(m, x, y, Tt);
        let idx;
        if (d === 0) idx = 0; else if (d === 1) idx = 1; else if (d === 2) idx = north ? 2 : 3;
        else {
          const h = hash32((tex ^ (Math.imul(x, 0x9e3779b1) >>> 0) ^ (Math.imul(y, 0x85ebca6b) >>> 0)) >>> 0) % 16;
          idx = h === 0 ? Math.min(3 + nf - 1, mid + 1) : (h === 1 ? Math.max(3, mid - 1) : mid);
        }
        sheet.px[(oy + y) * sheet.w + ox + x] = idx;
      }
    });
    return [sheet, masks];
  }
  function mapTiles(grid, edgePresent = false) {
    const table = indexTable(), h = grid.length, w = grid[0].length;
    return grid.map((row, y) => row.map((v, x) => {
      if (!v) return -1;
      let m = 0;
      for (const [dx, dy, bit] of NEIGH) {
        const nx = x + dx, ny = y + dy, inside = nx >= 0 && nx < w && ny >= 0 && ny < h;
        if ((inside && grid[ny][nx]) || (!inside && edgePresent)) m |= bit;
      }
      return table[m];
    }));
  }

  // ---------------------------------------------------------------- 9-slice
  function nineSlice(src, inset, w, h) {
    const Tt = src.w, mid = Tt - 2 * inset, out = new Sprite(w, h, src.palette);
    for (let y = 0; y < h; y++) {
      const sy = y < inset ? y : (y >= h - inset ? Tt - (h - y) : inset + (y - inset) % mid);
      for (let x = 0; x < w; x++) {
        const sx = x < inset ? x : (x >= w - inset ? Tt - (w - x) : inset + (x - inset) % mid);
        out.px[y * w + x] = src.px[sy * Tt + sx];
      }
    }
    return out;
  }

  // ---------------------------------------------------------------- dispatch
  function streamsFor(data, seed, overrides) { return new Streams(masterSeed(typeHash(data), seed), overrides); }
  function frames(data, seed, overrides) {
    const S = streamsFor(data, seed, overrides);
    if (data.generator === "mask") return maskFrames(data, S);
    if (data.generator === "lsystem") return lsystemFrames(data, S);
    if (data.generator === "parallax") return [parallaxLayers(data, S)[0][2]];
    if (data.generator === "autotile") return [buildTileset(data, S)[0]];
    throw new Error("generator " + data.generator + " is not in the JS core yet");
  }
  function streamPaths(data) {
    if (data.generator === "mask") return ["body"].concat((data.parts || []).map((p) => "part/" + p.name), ["shade", "eyes"]);
    if (data.generator === "lsystem") return ["grow", "step", "fruit"];
    if (data.generator === "parallax") return ["stars"].concat(data.layers.map((L) => "layer/" + L.name));
    return ["texture"];
  }
  function brood(data, a, b, child) {
    const h = typeHash(data), C = new Streams(masterSeed(h, child)), A = new Streams(masterSeed(h, a)), B = new Streams(masterSeed(h, b));
    const pick = C.rng("brood/pick"), overrides = {}, inherited = {};
    for (const p of streamPaths(data)) {
      const r = pick.below(100);
      if (r < 10) { inherited[p] = "mutation"; continue; }
      const src = r % 2 === 0 ? A : B;
      overrides[p] = src.seed(p); inherited[p] = src === A ? "A" : "B";
    }
    return { frames: frames(data, child, overrides), inherited };
  }
  const ALPHA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
  function shareCode(typeHashHex, seed) {
    let s = BigInt(seed); const sb = new Uint8Array(8);
    for (let i = 0; i < 8; i++) { sb[i] = Number(s & 255n); s >>= 8n; }
    const body = cat(Uint8Array.of(ENGINE_MAJOR), unhex(typeHashHex).slice(0, 8), sb);
    const raw = cat(body, sha256(body).slice(0, 2));
    let n = 0n, bits = 0, out = "";
    for (const byte of raw) { n = (n << 8n) | BigInt(byte); bits += 8; while (bits >= 5) { bits -= 5; out += ALPHA[Number((n >> BigInt(bits)) & 31n)]; } }
    if (bits) out += ALPHA[Number((n << BigInt(5 - bits)) & 31n)];
    return "PG-" + out.match(/.{1,5}/g).join("-");
  }

  return { ENGINE_MAJOR, sha256, hex, canonical, typeHash, Rng, derive, masterSeed, hash32, Streams, Sprite, hexToRgba,
    frames, parallaxLayers: (d, seed) => parallaxLayers(d, streamsFor(d, seed)), buildTileset: (d, seed) => buildTileset(d, streamsFor(d, seed)),
    mapTiles, nineSlice, blobMasks, brood, streamPaths, shareCode, COLS };
})();
if (typeof module !== "undefined") module.exports = PG;
