"""GUI slots — generated UI kits: 9-slice panels, button states, icons.

A theme type file (generator = "uikit") fixes material, border, corner and
colours; change the material and every panel, button and icon regenerates to
match. Kits export as a PNG atlas plus kit.json (slices and insets), a Godot
StyleBoxTexture resource and a CSS border-image rule, so the same art works in
this suite, in engines, and on the web.

9-slice rendering TILES edges and centre (never stretches), so pixels stay
square at any size.
"""

from __future__ import annotations

import json

from . import ENGINE_MAJOR
from .rng import M32, Streams, hash32, master_seed
from .sprite import TRANSPARENT, Sprite, blit, hex_to_rgba

STATES = ("normal", "hover", "pressed", "disabled")

ICON_TYPE = {
    "size": [9, 9], "mirror": True, "outline_style": "plain",
    "body": {"template": ["..1", ".12", "12#", ".12", "..1", "..."], "anchor": [1, 1]},
    "features": {"eyes": 0}, "animation": {"frames": 1},
}


def panel(data: dict, state: str = "normal", tex_seed: int = 0) -> Sprite:
    T, b = data["tile"], data["border"]
    mat = [hex_to_rgba(c) for c in data["palette"]["material"]]
    n = len(mat)
    pal = [TRANSPARENT, hex_to_rgba(data["palette"]["outline"])] + mat
    shift = {"normal": 0, "hover": 1, "pressed": 0, "disabled": -1}[state]
    hi, lo = n - 1, 0
    base = (n - 1) // 2 + shift
    base = max(1, min(n - 2, base))
    s = Sprite(T, T, pal)
    corner = data["corner"]
    for y in range(T):
        for x in range(T):
            cx, cy = min(x, T - 1 - x), min(y, T - 1 - y)
            if corner == "round" and cx + cy < b:
                continue
            if corner == "notch" and cx < b and cy < b:
                continue
            d = min(cx, cy)
            if corner == "round" and cx + cy == b:
                d = 0
            if d == 0:
                idx = 1
            elif d < b:
                idx = 2 + min(n - 1, lo + 1)  # frame band between outline and bevel
            elif d == b:
                top_left = y < T - 1 - y if cy <= cx else x < T - 1 - x
                bright = top_left if state != "pressed" else not top_left
                idx = 2 + (hi if bright else lo)
            else:
                idx = 2 + base
                if data.get("texture", 0) and hash32(tex_seed ^ ((x * 0x9E3779B1) & M32) ^ ((y * 0x85EBCA6B) & M32)) % 100 < data["texture"]:
                    idx = 2 + max(0, base - 1)
            if state == "disabled" and d <= b:
                idx = 2 + lo if d == b else 1
            s.px[y * T + x] = idx
    return s


def insets(data: dict) -> int:
    return data["border"] + 1


def nine_slice(src: Sprite, inset: int, w: int, h: int) -> Sprite:
    """Render src at w x h: corners copied, edges and centre tiled."""
    T = src.w
    if w < 2 * inset or h < 2 * inset:
        raise ValueError(f"9-slice target {w}x{h} is smaller than its corners ({2 * inset}x{2 * inset})")
    out = Sprite(w, h, list(src.palette))
    mid = T - 2 * inset
    for y in range(h):
        if y < inset:
            sy = y
        elif y >= h - inset:
            sy = T - (h - y)
        else:
            sy = inset + (y - inset) % mid
        for x in range(w):
            if x < inset:
                sx = x
            elif x >= w - inset:
                sx = T - (w - x)
            else:
                sx = inset + (x - inset) % mid
            out.px[y * w + x] = src.px[sy * T + sx]
    return out


def build_kit(tf, seed: int) -> dict:
    """Returns {'atlas': Sprite, 'kit': dict, 'panels': {state: Sprite}, 'icons': [Sprite]}."""
    from .gen import mask
    from .typefile import from_dict

    data = tf.data
    S = Streams(master_seed(tf.type_hash, seed, ENGINE_MAJOR))
    tex = S.rng("texture").next()
    panels = {st: panel(data, st, tex) for st in STATES}
    icons = []
    mat = data["palette"]["material"]
    for i in range(data.get("icons", 0)):
        icon_t = dict(ICON_TYPE, schema="pixelgoblin/type@1", id=f"{data['id']}.icon", tag="ui.icon",
                      generator="mask", license=data["license"],
                      palette={"outline": data["palette"]["outline"],
                               "ramps": [{"name": "mat", "weight": 1, "colors": mat[1:]}]})
        icons.append(mask.generate(from_dict(icon_t, "uikit-icon"), (S.rng(f"icon/{i}").next())))
    T = data["tile"]
    cols = max(len(STATES), len(icons))
    atlas = Sprite(cols * max(T, 9), T + (9 if icons else 0), [TRANSPARENT])
    kit = {"engine": ENGINE_MAJOR, "theme": data["id"], "tile": T, "insets": [insets(data)] * 4,
           "slices": {}, "icons": [], "license": data["license"]}
    for i, st in enumerate(STATES):
        blit(atlas, panels[st], i * T, 0)
        kit["slices"][f"panel.{st}"] = {"x": i * T, "y": 0, "w": T, "h": T}
    for i, ic in enumerate(icons):
        blit(atlas, ic, i * 9, T)
        kit["icons"].append({"x": i * 9, "y": T, "w": 9, "h": 9})
    return {"atlas": atlas, "kit": kit, "panels": panels, "icons": icons}


def godot_stylebox(kit: dict, atlas_path: str, state: str = "normal") -> str:
    r = kit["slices"][f"panel.{state}"]
    i = kit["insets"][0]
    return (f'[gd_resource type="StyleBoxTexture" load_steps=2 format=3]\n\n'
            f'[ext_resource type="Texture2D" path="res://{atlas_path}" id="1"]\n\n[resource]\n'
            f'texture = ExtResource("1")\nregion_rect = Rect2({r["x"]}, {r["y"]}, {r["w"]}, {r["h"]})\n'
            f'texture_margin_left = {i}\ntexture_margin_top = {i}\ntexture_margin_right = {i}\ntexture_margin_bottom = {i}\n'
            f'axis_stretch_horizontal = 1\naxis_stretch_vertical = 1\n')


def css_border_image(kit: dict, panel_png: str, scale: int = 4) -> str:
    i = kit["insets"][0]
    return (f".pg-panel {{\n  border: {i * scale}px solid transparent;\n  border-image: url('{panel_png}') {i} fill / {i * scale}px repeat;\n"
            f"  image-rendering: pixelated;\n}}\n")


def kit_json(kit: dict) -> str:
    return json.dumps(kit, indent=2, sort_keys=True)
