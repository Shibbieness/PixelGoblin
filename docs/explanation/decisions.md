# Decisions (ADRs)

Format: **Context → Decision → Consequences.** ADR-001 to ADR-008 are from the design document of 2026-09-24. ADR-009 onward were made during the prototype build.

| ADR | Decision | Status |
|---|---|---|
| 001 | One core, many thin bindings | Kept; the core is Python for now (see 009) |
| 002 | Integer-only runtime; floats only at tool time | **Built and gated** (B02 refuses floats, B13 proves cross-language) |
| 003 | Model-free core; ML is an optional plug-in | Built: there is no ML anywhere |
| 004 | Own quantiser; no libimagequant | Built: seeded-free k-means in OKLab |
| 005 | TOML authored, canonical JSON hashed | Built with SHA-256 (BLAKE3 is not in the stdlib) |
| 006 | Editor UI in Rust + egui | **Superseded by 011** for the prototype |
| 007 | Aseprite interop from the public spec only | Planned (P6); Aseprite-style sheet JSON ships now |
| 008 | Named sub-seed streams per part | **Built and gated** (B01, and a falsify mutation) |

## ADR-009 — Python reference engine before Rust (reverses the build order)

**Context.** The design said: build the Rust core first. That was the right call for speed, but three things pointed the other way for the prototype. Book of Cities is sovereign Python and the first real consumer. The stack's discipline (SPIRE, Vanilla Core, ASSAY) is stdlib-only Python with zero dependencies. And a determinism contract needs an **oracle** to port against.

**Decision.** The prototype engine is stdlib-only Python. It is the reference implementation and the owner of the goldens. The Rust core (P1) must reproduce its goldens byte for byte.

**Consequences.** + Runs today with nothing installed. + Imports directly into Book of Cities. + The goldens become the spec for every later port. − Slower than Rust; fine for tools and load-time generation, and not for per-frame generation of large crowds.

## ADR-010 — Licensing: follow the stack's existing pattern

**Context.** Mark wants it open source "unless they want to pay for it". QRen Coder and Vanilla Core already solve this exact problem: AGPL-3.0-or-later, plus a placeholder commercial licence, plus a small §7(b) attribution term, with the bigger credit obligation kept in the private commercial contract.

**Decision.** PixelGoblin uses the same three files, with the same wording and structure. Two additions specific to pixel art:
1. **Output is not covered by the engine's licence.** Each type file's `license` field states the licence of the *sprites* it makes, and that licence is written into every export's provenance.
2. **Vanilla type files make CC0 sprites.** This gets the art out there with no strings. Book of Cities flavor types are `Proprietary`.

**Consequences.** + Indies and jams pay nothing and owe only a credit line. + Closed-source games that embed the runtime are the natural buyers of the commercial licence. − The commercial terms still need a lawyer (placeholder).

## ADR-011 — Editor as one offline HTML page, with a parity-gated JavaScript core

**Context.** An egui editor needs the Rust core, which does not exist yet. A page that runs in any browser can be opened today, shared as a link, and embedded.

**Decision.** `editor/pixelgoblin.html` is built from `editor/src.html` and `editor/pg-core.js`, a line-for-line port of the integer runtime. Gate B13 runs `pg-core.js` under node and requires identical pixels, type hashes and share codes for every golden.

**Consequences.** + A usable editor now, on any device. + A second-language proof of the determinism contract. − Two implementations to keep in step. The gate makes drift loud rather than silent.

## ADR-012 — What was ported from SPIRE, and what was not

**Decision.** Port the gate discipline: namespaces, falsification, vacuity guards, ratchets, from-empty, full-run status, socket guard, two verdicts, mechanism-first hazards, scrub on code not prose, and the longevity export. Do **not** port the hazard register's full shape, held-out splits, or the seven-store layout. See `gates.md` for the reasons.

## ADR-013 — Two verdicts: spec and target

**Context.** "Is this goblin right?" and "can the NES show this goblin?" are different questions. Merged, a platform limit reads as a design error.

**Decision.** `spec_verdict` (SOUND / UNSOUND) and `target_verdict` (FITS / DOES_NOT_FIT) are separate functions with no combined field. Gate B08 and a falsify mutation hold this.

## ADR-014 — The hazard layer: flashing and licences only

**Context.** Pixel art tools make animations. Fast light/dark flashing can trigger seizures.

**Decision.** Animation exports run an approximate WCAG-style general-flash check. Findings are labelled UNVERIFIED, because this is not a certified test, and are delivered in SPIRE's order: don't, what happens, why, what instead. Detection reports and never blocks on its own. Blocking is a bundle-profile judgement, used only for commercial packs with non-commercial inputs.

—Shibbieness
—Claude
