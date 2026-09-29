# capsules/

The built files, ready to install in Claude. Each is made from this repository by `tools/package.py`.

**The files themselves are not in this repository.** It is public, and the workshop carries the link to the private session it was built in (its `codex/LINEAGE.md` and `META.json`), which is exactly what the leak guard exists to keep out. The guard reads text and cannot see inside a zip, so it did not catch them. Mark holds the built files; put them here by hand to rebuild the workshop, and check them against the fingerprints below. `.gitignore` keeps them from being committed again.

| File | What it is | Install it as |
|---|---|---|
| `pixelgoblin-workshop-v1u0p1.skill` | **The one to upload.** The whole project as a skill: 129 files (the upload limit is 200). The repository rides inside as one bundle, and the original capsule rides inside unchanged. | a skill |
| `pixelgoblin-pseudoskill-v1u0p1.skill` | The original capsule, frozen. 1,058 files, so it cannot be uploaded as a skill; kept as the reference the workshop carries. | not installable as is |
| `pixelgoblin.plugin` | The plugin: three skills and nine drawing tools. | a plugin |

## Fingerprints (SHA-256)

| File | SHA-256 |
|---|---|
| `pixelgoblin-pseudoskill-v1u0p1.skill` | `38b1561d08b9d7c8f57470f92d663d0e16d2ef3b2f910d288d2098925ed4f66c` |
| `pixelgoblin-workshop-v1u0p1.skill` | `f5b650460fae48700ce03ec755e809a3f88f22238241302a67a824694d0e3902` (forged from 256d615) |
| `pixelgoblin-workshop-v1u0p0.skill` | `80565e2007ab2743dabfc1cf32e7fe970a2388fc7b4ab6b0711fffd8d6a2ea17` (superseded) |
| `pixelgoblin.plugin` | `68876bffc565024954954018d673bbdde55525c0be49b9f631c929678a822a5e` (forged from 256d615; was `60b3c3c7…`) |

The original's fingerprint is also pinned in `tools/packaging_workshop.py`; the workshop forge refuses to run if it changes.

## Rebuilding

```
python3 tools/package.py            # the plugin and the workshop, into dist/
python3 tools/package.py workshop   # the workshop only
```

The workshop forge finds the frozen original here (or in `dist/archive/`), checks its fingerprint, and packs it inside the new workshop unchanged.

This folder is never packed into a capsule, so built files never nest inside each other.

—Shibbieness
—Claude
