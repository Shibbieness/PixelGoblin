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
PGRig.setTables(input.teams || {}, input.owns || {});
PGRig.setPacks(input.packs || []);
const typeOf = (c) => {
  let d = c.overlay ? PGRig.compose(c.type, c.overlay.own, c.overlay.id) : c.type;
  for (const o of c.overlays || []) d = PGRig.compose(d, o.own, o.id);
  if (c.team) d = PGRig.withTeam(d, c.team);
  return d;
};
const out = input.cases.map((c) => {
  if (c.kind === "sandbox") return { plan: PGRig.sandboxWorld(c.biome, c.seed, c.w, c.h) };
  if (c.kind === "view") {
    const data = typeOf(c);
    const g = PGRig.genome(data, PGRig.streamsFor(data, c.seed));
    return { hashes: c.views.map(([v, t, yaw, pitch, pose]) => PGRig.renderView(data, g, t, { view: v, yaw, pitch, pose }).sprite.pixelHash()) };
  }
  if (c.kind === "beast") {
    const g = PGRig.beastGenome(c.type, PGRig.streamsFor(c.type, c.seed));
    return { genome: g, hashes: c.views.map(([v, t, pose]) => PGRig.beastRender(c.type, g, t, { view: v, pose }).sprite.pixelHash()) };
  }
  if (c.kind === "mounted") {
    const g = PGRig.genome(c.type, PGRig.streamsFor(c.type, c.seed));
    const bg = PGRig.beastGenome(c.beast, PGRig.streamsFor(c.beast, c.beast_seed));
    return { hashes: c.views.map(([v, t]) => PGRig.mounted(c.type, g, c.beast, bg, t, { view: v }).sprite.pixelHash()) };
  }
  if (c.kind === "zoom") {
    const g = PGRig.genome(c.type, PGRig.streamsFor(c.type, c.seed));
    return { hashes: PGRig.zoomFrames(c.type, g, c.from, c.to, c.steps).map((f) => f.pixelHash()) };
  }
  if (c.kind === "city") {
    const people = PGRig.census(c.city, PGRig.parseNames(c.names));
    const img = PGRig.cityVillage(c.city, people, c.seed);
    return { people: people.map((p) => [p.name, p.role, p.sub, p.team, p.household, p.age_group, p.band, p.parents, p.inherited || null, p.outdoors]),
             hashes: [img.pixelHash()].concat(people.slice(0, c.sprites).map((p) => PGRig.citizenSprite(p, 32).pixelHash())) };
  }
  if (c.kind === "rig") {
    const data = typeOf(c);
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
