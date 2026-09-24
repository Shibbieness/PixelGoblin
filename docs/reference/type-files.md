# Type-file reference

Type files are TOML. Every field is a whole number, text, true/false, a list or a table. **Decimal numbers are refused**, so every platform generates the same pixels.

## Every type file

| Field | Required | Meaning |
|---|---|---|
| `schema` | yes | `"pixelgoblin/type@1"` |
| `id` | yes | dotted name, unique, no spaces |
| `tag` | yes | dotted tag; its root must be in `types/tags.toml` |
| `generator` | yes | `mask`, `lsystem`, `parallax`, `autotile`, `uikit` |
| `license` | yes | the licence of the **sprites** this file makes |
| `size` | yes | `[width, height]`, 4 to 512 |
| `extends` | no | id of a parent type; tables merge, lists replace |

## `mask` — creatures, items, icons, fungi

| Field | Meaning |
|---|---|
| `mirror` | `true` makes the templates half-width and mirrors them |
| `outline_style` | `selout` (tinted by the body) or `plain` |
| `max_colors` | optional promise, checked by the spec verdict |
| `palette.outline` | outline colour |
| `[[palette.ramps]]` | `name`, `weight` (0 = only when named), `colors` (2 to 8, dark to light) |
| `[body]` | `template` (rows of `. 1 2 #`), `anchor` `[x, y]`, optional `ramp` |
| `[[parts]]` | `name` (unique), `chance` 0 to 100, `template`, `anchor`, optional `ramp` |
| `[features]` | `eyes` 0 to 2, `eye_color`, `eye_band` `[top%, bottom%]` of body height |
| `[animation]` | `frames` 1 to 8, `frame_ms` 16 to 2000 (bob and blink idle) |

A template plus its anchor must fit inside `size`, with a 1-pixel border for the outline.

## `lsystem` — trees, shrubs, coral, roots

`axiom`, `rules` (symbol to a list of `{to, weight}`), `iterations` 1 to 6, `step` `[min, max]`, `leaf_radius` 0 to 3, `fruit_chance`, `trunk_width` 1 or 2, `palette.bark`, `palette.leaf`, `palette.outline`, `palette.fruit`.

Symbols: `F` forward, `+` and `-` turn 45°, `[` push, `]` leaf then pop, `L` leaf.

## `parallax` — backdrops

`palette.sky` (top to bottom), `palette.star`, `stars`, and `[[layers]]` with `name`, `colors` (dark to light), `base` (% of height), `periods` and `amps` (one entry per noise octave), and `scroll` (%).

## `autotile` — terrain

`tile` 8 to 32, `palette.fill` (3 or more), `palette.outline`, `palette.highlight`.

## `uikit` — GUI slots

`tile`, `border` 1 to 3, `corner`, `icons` 0 to 16, `texture` (% speckle), `palette.material` (4 to 8), `palette.outline`.

## Tags and profiles (`types/tags.toml`)

`[roots]` lists the allowed first segments. `[tag."a.b"]` tables are conversion profiles: `size`, `colors`, `outline`, `dither`, `downsample`, `palette`, `cleanup`. A misspelled root is refused with a "did you mean".

—Shibbieness
—Claude
