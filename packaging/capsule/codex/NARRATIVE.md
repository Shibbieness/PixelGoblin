# NARRATIVE — PixelGoblin

Tags: #narrative #complete #origin #pivot

The story of how PixelGoblin came to be, session by session, and why it is shaped the way it is. For what each part does, see the mini-indexes. For the formal decision records, see `build/specs/explanation/decisions.md`.

---

## The through-line

**One small, honest engine that always draws the same thing from the same words.** Every session added a new way to see a goblin (a new size, a new side, a new colour, a new crowd), and every addition had to keep that promise and prove it with a gate.

## Session 1 — the design (2026-09-24) #origin #session:1

Mark asked for a pixel-art generator and editor suite. The design document set the eight founding decisions (ADR-001 to ADR-008): one core with thin bindings; an integer-only runtime so every platform makes the same pixels; a model-free core with any ML only as an optional plug-in; its own colour quantiser; type files authored in TOML and hashed as canonical JSON; an editor (then planned in Rust with egui); Aseprite interop from the public spec only; and named random streams per part, so adding an ear never changes a nose. The design named three ways to make art (generate, convert, learn) and the GUI slots for UI kits.

## Session 2 — the name, the build, the discipline (2026-09-24) #v1-design #naming #pivot #session:2

Mark asked to name it, build it, add SPIRE's logic and make it open source unless people pay. It became **PixelGoblin**. Two pivots happened here:

- **Python before Rust** (ADR-009). A standard-library Python reference engine could be built and gated in one session; Rust will later be bound to Python's goldens. The build order reversed, not the destination.
- **One offline HTML page instead of egui** (ADR-011). The editor became a single file anyone can open, with a JavaScript core proved pixel-identical to Python (gate B13).

SPIRE's discipline came across whole where it fit (ADR-012): plan and build gates, falsification with restore-on-start, vacuity guards, the count ratchet, from-empty runs, a status file written only after a full run, two verdicts that are never merged (ADR-013), and a hazard layer that reports flashing and licence risks by mechanism (ADR-014). Licensing followed the stack's pattern (ADR-010): AGPL-3.0-or-later with a commercial licence intended, an attribution line, and vanilla content kept free of stack terms by a scrub. PixelGoblin became the second real Vanilla Core flavor, and a bug in Vanilla Core's composite runs was found and fixed as a patch for Mark.

## Session 3 — the goblins (2026-09-25) #tier-chain #revision #session:3

Mark brought reference images and asked for a 27-role goblin roster, sizes from 8 to 256 px with eras, build bit chains, a fix for goblins with three legs, and a village. This is where the **rig** was born (ADR-015): a genome that never sees the tier, drawn at six tiers with a level-of-detail ladder, and eras as looks rather than sizes (ADR-016, because "8-bit" names a console, not a sprite size). The "three legs" bug came from the old template's merged centre column; the fix became a gate that draws legs twice and has a three-leg control. Colour ramps drew on CRUCIBLE's materials (a metal's resistivity shapes its glint). The village placed real characters from their role files. The JavaScript geometry stopped being hand-ported and started being **transpiled** from Python (ADR-017), which is why parity has held since. Mark's reference images stayed private: palettes were derived from them, their hashes recorded, the images never published.

## Session 4 — every side, every size, every citizen (2026-09-26) #views #city #validated #session:4

Mark asked, in order, for role signatures, expression sheets, team colours, mounts, side and back views, a smooth zoom from crowd to portrait, and a city built from a list of names; then front, sidescroller, isometric, top-down and free-rotate views that "build from each other".

The key decision (ADR-018) was how views build from each other. Carving a model from hand-drawn front, side and top drawings was **rejected** (#rejected), because generated characters have no hand-drawn side view to carve with. Instead the front drawing is **lifted** into one model and every view is drawn from it, so views cannot disagree; gate B18 checks heights, widths and depths like a draughtsman. Mounts were built as solids from the start (ADR-020). A citizen is decided by their own name (ADR-019), so adding one person changes nobody else. Signatures made every job readable at 8 px. Bugs caught on the way: the 3D mouth vanishing behind the nose (fixed by the decal layer rule), arms and chins sinking into clothes, shields inside bodies, ears invisible edge-on, boxy skirts, and signatures hiding feet at 8 px, which the legs gate caught.

## Session 5 — reaching it from anywhere (2026-09-26) #access #milestone #session:5

Mark asked for a widget, a plugin for all of it, access "here and in future chats", and everything packaged as a PseudoSkill. Three surfaces came out, each for a different moment:

- **PixelGoblin Pocket**, a published widget: type a name, turn the goblin, save it. For when Mark just wants a goblin.
- **The pixelgoblin plugin**: three skills and six MCP tools that return pictures inline, with the whole engine inside. For making art and extending the engine from Claude.
- **This capsule**: the project's memory, forged in Compound mode with the dense-session protocol, validated by the Forge checklist as code.

A new gate, **B21**, checks all three: the widget is current, the plugin is valid and its server draws byte-identical pictures, and the capsule passes the checklist. Three new mutations prove B21 notices: a server that lets the engine print into the protocol stream, a tool that returns no picture, and a validator that forgets a checklist item. ADR-021 records the decision: three ways in, one engine behind them.

## Session 5, continued — the worlds come in (2026-09-26) #packs #grounds #session:5

Mid-session Mark asked for more: basic resource packs of and for everything in the Book of Cities, the Compendium and the Aether Library; a sandbox and minigame area using CRUCIBLE and VI Builder; everything tuned stable, tied in and usable; and an honest round of what breaks, what fixes it, and what goes in between.

The packs were built the way the engine builds everything: from data, by a script, with a gate. Each source was extracted once into a catalog; `tools/build_packs.py` turns catalogs into type files (ADR-022). The key choice was to make every **folk** an **overlay**, like the goblin subspecies, so that any job can be any folk, and to let overlays **stack**, so a Compendium trait sits on top. Folk needed height, so the rig learned **stature**, drawn only when a species sets it, so no existing goblin moved. Ores took CRUCIBLE's densities, and the three fantasy metals stayed ungrounded, because CRUCIBLE says fantasy stays fantasy. Aether souls became avatar seeds that are **supplements**, honouring the Aether Library's supplement-but-never-overwrite rule.

**Goblin Grounds** (ADR-023) became the place where it all has to work together: a biome's residents, a folk goblin, CRUCIBLE weights and a forge's quests. The world planner was written in the transpiler's subset, so the page and `world.json` are the same world (#validated by gate B23, down to a 64-bit seed). VI Builder had no manifest to fill, so PixelGoblin registered the way LEXIS and LATTICE already do.

The break-and-fix round found real things: the variety gate expected creatures, not icons (now a stated `variety_min`); mask parts off-centre broke the mirror verdict; type lookup slowed tenfold with 330 more files (now indexed); vanilla code had picked up stack words (reworded, and the scrub caught it); flowers drew as bare sticks (new forms). Each became a check.

## What the story teaches

- The engine grew by adding **views of one thing**, never second copies of it. The tier chain is one genome; the views are one model; the city is one census; the browser is one transpiled source.
- Every "fix" became a gate with a control, so it could not come back.
- The honest weak spots are always the same kind: places where art direction was replaced by a rule (inferred side views, simple households). The next step is art direction as data.

---
—Shibbieness
—Claude
