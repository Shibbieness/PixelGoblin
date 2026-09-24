// Parity runner for build gate B13: reads cases (JSON) on stdin, runs the exact
// pg-core.js text the editor embeds, prints hashes for Python to compare.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const here = dirname(fileURLToPath(import.meta.url));
const PG = new Function(readFileSync(join(here, "pg-core.js"), "utf8") + "\n;return PG;")();
const cases = JSON.parse(readFileSync(0, "utf8"));
const out = cases.map((c) => ({
  type_hash: PG.typeHash(c.type),
  hashes: PG.frames(c.type, c.seed).map((f) => f.pixelHash()),
  share: PG.shareCode(PG.typeHash(c.type), c.seed),
}));
process.stdout.write(JSON.stringify(out));
