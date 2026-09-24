# Make a UI kit

1. Copy `types/vanilla/ui.stone.toml`. Change `id`, `palette.material` (5 colours, dark to light), `corner` (`square`, `round`, `notch`) and `border` (1 to 3).
2. Build it:
   ```
   python3 -m pixelgoblin uikit my.ui.bronze --seed 1 --out kit/
   ```
3. You get:

| File | Use |
|---|---|
| `atlas.png` | all panels, button states and icons |
| `kit.json` | where each slice is, and the insets |
| `panel_normal.tres` | Godot `StyleBoxTexture`, ready to use |
| `panel.css` | CSS `border-image` rule for web UIs |
| `preview.png` | the panel drawn at 64x32 |

## Why panels stay crisp

9-slice rendering **tiles** the edges and centre instead of stretching them. Pixels stay square at any size. Gate B06 draws panels at five sizes and checks that the outline never breaks.

## Button states

`normal`, `hover` (one step lighter), `pressed` (bevel flips) and `disabled` (flattened). All four come from the same theme, so they always match.

## Theme the editor itself

The editor's **Swap sides** and **Readable** buttons are the first custom-layout slots. Skinning the editor with a generated kit is on the gameplan (P5).

—Shibbieness
—Claude
