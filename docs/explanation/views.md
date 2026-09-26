# Views: side, back, isometric, top-down and free rotation

This page explains how PixelGoblin draws a character from any direction, why the views agree with each other, and where the method stops being good enough. It answers Mark's request for "front, sidescroller, a few isometric views, top-down, and free rotate from the composition of the previous views, built from each other".

## The honest version of "built from each other"

There are two ways to make views build from each other.

1. **Carve a model from drawings.** Draw the front, the side and the top by hand, then keep only the space that all three drawings agree is filled (a "visual hull"). This is how a modeller works from reference sheets.
2. **Lift one drawing into a model, and draw every view from the model.** Author the front, give each part a depth rule, and let one model produce the side, back, isometric and top-down views.

PixelGoblin does the second. Characters are *generated*, not hand-drawn, so there is no hand-drawn side view to carve with. What still holds is the part of the request that matters: every view comes from the same model, so the views cannot contradict each other. And the one drawing that *is* authored, the front, is checked against the model's own front view.

## Step 1: lift

Every shape in the front drawing becomes a solid, according to what it is.

| Part | Becomes | Why |
|---|---|---|
| head, hands, feet, nose, eyeballs | ellipsoids | round things stay round from any side |
| arms, legs, staffs, spears, braids | 3D capsules | a capsule looks the same from every direction around its axis |
| torso, tunic, belt, apron, bands | rounded boxes with an elliptic front-to-back profile | clothes wrap the body; each layer is a little deeper than the one under it |
| skirts, robes | the drawn outline, rounded front to back | the same rule, for flared shapes |
| hair, hood, helm, cap, headscarf | a dome over the head with an opening for the face | from the front you see the face through it; from behind, only hair |
| ears, fins, earrings | thin plates, swept back | goblin ears lie back a little, so they read from the side and from above |
| backpacks, capes, quivers | solids behind the back | they appear only where the body does not hide them |
| held items | at the hand, just in front of the palm; pushed in front of the body when held across it | a shield or a lute is never inside the goblin |
| eyes, brows, mouths, patterns, straps, buckles | **decals** | painted onto the front of whatever they were drawn over |

Two proportions are set in 3D that the front drawing cannot show. The head sits forward of the chest (goblins stoop), and the arms hang slightly forward of the torso's sides.

**Decals** follow the front drawing's own rule: a decal covers anything on a lower layer, projected straight back from the front, onto front-facing surfaces only. That is why eyes appear on the profile in a side view and vanish in the back view, and why a tunic's pattern never shows on the back of the tunic.

## Step 2: voxels

The solids fill a grid of N×N×N voxels, one voxel per pixel of the tier. Where two solids overlap, the one drawn later in the front view wins, exactly as it did in 2D.

## Step 3: views

An orthographic camera looks at the grid from any **yaw** and **pitch**, in whole degrees:

| Name | Yaw | Pitch | Use |
|---|---|---|---|
| `front` | 0 | 0 | the front drawing, rebuilt from the model |
| `side_right` / `side_left` | 270 / 90 | 0 | sidescrollers |
| `back` | 180 | 0 | walking away |
| `iso_se` / `iso_sw` / `iso_ne` / `iso_nw` | 315 / 45 / 225 / 135 | 30 | isometric games, four facings |
| `three_quarter` | 0 | 45 | top-down RPG camera |
| `top` | 0 | 90 | straight down |
| any | 0 to 359 | 0 to 90 | free rotation (drag the picture in the workbench) |

Each pixel's ray is marched through the grid, and the first voxel it meets decides the pixel. Light comes from the viewer's upper left, whatever the angle. The finish is the front drawing's own: shade bands, contact shadows, outline, era colour budget. A 30° view is taller than it is wide (64 × 88 at 64 px), so a standing character still fits.

**Walking in a sidescroller:** the `walk_side` motion moves the legs forward and back in depth and swings the arms against them. The front drawing's walk can't do that, because in a front view a stride goes toward the viewer.

## Why the views agree

All views are projections of one grid, so they obey the draughtsman's rules:

- front and side share **heights**;
- front and top share **widths**;
- side and top share **depths**.

Gate B18 checks all three on every third role. It also checks that the model's front view reproduces the front drawing, and that faces are hidden from behind. A control shows that a view one row off would be caught.

Measured this run: the model's front view covers the drawing's silhouette almost exactly (IoU about 98%) and matches its materials on about 93% of pixels. Most of the difference is where an arm's inner edge meets a tunic: the 2D drawing layers the arm on top, but in 3D the tunic's curve comes forward past it.

## Mounts are built the other way round

A boar or a warg is long from front to back, so a front drawing would say almost nothing about it. Mounts are built directly as solids in a cube twice the size (2048 units), so a goblin fits on top at the same scale. Every view then comes free. A rider is the rider's own lifted model with the legs re-posed astride (thighs forward over the flanks, boots in the stirrups), moved onto the saddle. The rider's decals are marked as the rider's own, so a rider's eyes never get painted onto the boar.

## Where it breaks

- **Side and top views are inferred, not art-directed.** A hand-drawn side view would exaggerate the nose and the ears for readability. The fix is per-feature depth overrides as data, like `items`.
- **Blocky at small sizes.** At 16 px a turnaround is legible but crude. Isometric games usually use 32 px and up.
- **One pose.** Views rotate the idle and walk poses; there is no crouch, attack or sit yet, except the seated rider.
- **Hard 3D cases.** A cape and a backpack worn together, or a very long held item crossing the face, can meet in ways no front drawing implied.

—Shibbieness
—Claude
