// Parity runner for build gate B13: reads cases (JSON) on stdin, runs the exact
// script text the editor embeds (pg-core.js + pg-rig.js with the generated
// geometry spliced in), prints hashes for Python to compare.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const here = dirname(fileURLToPath(import.meta.url));
const read = (f) => readFileSync(join(here, f), "utf8");
const script = read("pg-core.js") + "\n" + read("pg-rig.js").replace("/*__RIG_GEN__*/", read("pg-rig.gen.js"));
const { PG, PGRig } = new Function(script + "\n;return { PG, PGRig };")();
const input = JSON.parse(readFileSync(0, "utf8"));
const types = input.types || {};
PGRig.setResolver((id) => { if (!types[id]) throw new Error("unknown type " + id); return types[id]; });
const out = input.cases.map((c) => {
  if (c.kind === "rig") {
    const data = c.overlay ? PGRig.compose(c.type, c.overlay.own, c.overlay.id) : c.type;
    const g = PGRig.genome(data, PGRig.streamsFor(data, c.seed));
    const r = {};
    r.type_hash = PG.typeHash(data);
    r.genome = g;
    r.hashes = c.tiers.map((t) => PGRig.render(data, g, t, { era: c.era || null, rim: !!c.rim, pose: c.pose || {} }).sprite.pixelHash());
    r.legs = c.tiers.map((t) => PGRig.legsCheck(data, g, t).ok);
    return r;
  }
  if (c.kind === "family") {
    const fam = PGRig.family(c.type, c.founders, c.seed);
    const hs = fam.children.map((k) => PG.frames(c.type, k.seed, k.overrides)[0].pixelHash());
    hs.push(PG.frames(c.type, fam.grandchild.seed, fam.grandchild.overrides)[0].pixelHash());
    return { hashes: hs, inherited: fam.grandchild.inherited };
  }
  return {
    type_hash: PG.typeHash(c.type),
    hashes: PG.frames(c.type, c.seed).map((f) => f.pixelHash()),
    share: PG.shareCode(PG.typeHash(c.type), c.seed),
  };
});
process.stdout.write(JSON.stringify(out));
