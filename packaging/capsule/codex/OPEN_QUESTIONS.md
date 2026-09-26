# OPEN QUESTIONS — PixelGoblin

Tags: #open-questions #open #session:5

Unresolved decisions and known unknowns at forge (2026-09-26). Each has what is known, what is not, and what would settle it.

---

## Q1 — Should side and top views be art-directed? #open-question

- **Known:** views are inferred from the front drawing by depth rules; they agree with each other (B18) but a pixel artist would push a profile nose or tilt an ear for readability.
- **Proposed:** per-feature depth overrides as data in role files, checked by the same agreement gate.
- **Settles it:** Mark judging the side views in the gallery.

## Q2 — How should small 3D views be drawn? #open-question

- **Known:** at 16 px a turnaround is legible but blocky.
- **Proposed:** render the view at twice the size and reduce it with the chain's own rules (snap, signature) instead of voxelising at 16.
- **Settles it:** a side-by-side test at 16 and 32 px.

## Q3 — Pose as data #open-question

- **Known:** one pose family (idle, walk, side walk, seated). Limbs are capsules with two ends, so the lift already supports joint angles.
- **Proposed:** poses as joint angles in type files (attack, crouch, sit, carry). Recommended next feature: it unlocks every view at once.

## Q4 — The last 7% of front agreement #open-question

- **Known:** the model's front matches the drawing on about 93% of the silhouette. Where an arm meets a tunic, the 3D tunic curves in front of the arm.
- **Proposed:** let the 2D layer order nudge depth where two solids nearly touch.

## Q5 — Richer households and mounts #open-question

- **Known:** households are two parents then children; riders use generic seated thighs; big capes can clip a mount.
- **Proposed:** relations as explicit lines in the names file (`Tok Ashfang < Grubnak, Mizzle`); a saddle anchor per mount kind and a cape rule.

## Q6 — Re-bless the session 4 goldens #open-question

- **Known:** 103 goldens changed on purpose in session 4 (signatures, the 8-bit eye rule, props). Claude witnessed the re-bless; Mark has not.
- **Settles it:** Mark looks at the gallery (`build/assets/gallery/`) and re-blesses with his name as witness.

## Q7 — Validate the 16 newest SLM-e pieces #open-question

- **Known:** 32 pieces in `slme/pieces.json`; the first 16 passed SLM-e's `validate_manifest`; the 16 added since could not be checked from the build sessions.
- **Settles it:** run SLM-e's validator once, then register all 32 in `slme.db`.

## Q8 — Apply the Vanilla Core composite-run patch #open-question

- **Known:** `patches/vanilla-core-composite-fix.patch` fixes two flavors sharing an entry-module name; the QRen example needs it. Mark's repos are read-only to Claude.
- **Settles it:** Mark applies the patch.

## Q9 — Capsule naming convention #open-question

- **Known:** the output spec names capsules `<project>-codex`; Mark's recent capsules use `<project>-pseudoskill`. This capsule follows the recent practice: `pixelgoblin-pseudoskill`.
- **Settles it:** Mark says which convention is canonical.

## Q10 — Where should the plugin's MCP server run? #open-question

- **Known:** the server needs Python 3.11 on the machine that runs it. It was tested from the packaged plugin in a clean folder. Surfaces that do not run local servers still get the skills and the published pages.
- **Settles it:** installing the plugin on Mark's desktop and running `pixelgoblin_selftest`.

## Q11 — The Rust core and other bindings #open-question

- **Known:** designed in `build/specs/explanation/gameplan.md` (P1 Rust core bound to Python's goldens; P7 bindings). Not started.

## Q12 — GILWRIGHT products and the commercial licence #open-question

- **Known:** first product candidates are the vanilla type-file pack (CC0 sprites), a UI kit pack, and the engine under the commercial licence. `LICENSE-COMMERCIAL.md` describes intent, not terms.
- **Settles it:** Mark's pricing and terms.

## Q13 — Canonical palettes for the packs #open-question

- **Known:** the source documents rarely state colours, so most pack colours are inferred from names ("rust red", "sea-green") and flagged.
- **Settles it:** Mark states palettes for the folk, biomes and key materials; they go into the source catalogs and `tools/build_packs.py` regenerates.

## Q14 — Horns, tails and wings for folk #open-question

- **Known:** overlays change the body but ignore `[role]`, so a folk cannot add headwear such as horns; the rig has no tail or wing feature.
- **Proposed:** body features as species accessories (horns, tail, wings) on the LOD ladder, lifted into the 3D views like ears.

## Q15 — Goblin Grounds, the next layer #open-question

- **Known:** gathering, weight, quests and the forge work; animals wander in the page only; the forge smelts without recipes.
- **Proposed:** recipes from the world catalog's stations (tiers IMPROVISED to LEGENDARY), animals in the world plan, and isometric Grounds using the characters' iso views.

## Q16 — VI Builder's registry #open-question

- **Known:** VI Builder is Phase 0 (architecture); there is no registry or API to call. PixelGoblin's registration profile and process_record are ready for it.
- **Settles it:** VI Builder Phase 1.

## Q17 — Pack sprites beyond body plans #open-question

- **Known:** animals, fungi and ores use a small set of mask templates, so a deer and a bison share a body plan.
- **Proposed:** per-creature templates for the ones Mark cares about most, or the rig's lift applied to beasts (like the boar and warg).

---
—Shibbieness
—Claude
