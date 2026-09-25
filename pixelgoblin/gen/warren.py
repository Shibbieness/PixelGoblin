"""Warren — dungeons as graphs first, tiles second.

A dungeon is laid out as a small directed graph of rooms (entrance first,
the hardest room farthest away), then carved into a tile grid and drawn with
any autotile terrain type. The graph is returned as data, so a game can hang
encounters, keys and loot on it; the tiles regenerate from the same seed.

Integer-only. Rooms are placed by seeded rejection sampling with a one-tile
margin; every room connects to its nearest earlier room (so the graph is
always connected), with a few extra forward edges for loops.
"""

from __future__ import annotations

from .. import ENGINE_MAJOR
from ..rng import Streams, master_seed, sha256
from ..sprite import Sprite, hex_to_rgba


def identity(tf) -> str:
    from ..typefile import load
    return sha256((tf.type_hash + load(tf.data["terrain"]).type_hash).encode()).hex()


def layout(tf, seed: int, overrides=None) -> dict:
    d = tf.data
    W, H = d["size"]
    S = Streams(master_seed(identity(tf), seed, ENGINE_MAJOR), overrides)
    r = S.rng("rooms")
    lo, hi = d["room_size"]
    rooms = []
    for _ in range(d["attempts"]):
        if len(rooms) >= d["rooms"][1]:
            break
        w, h = r.range(lo, hi), r.range(lo, hi)
        x, y = r.range(1, max(1, W - w - 2)), r.range(1, max(1, H - h - 2))
        if all(x + w + 1 < rx or rx + rw + 1 < x or y + h + 1 < ry or ry + rh + 1 < y for rx, ry, rw, rh in rooms):
            rooms.append((x, y, w, h))
    if len(rooms) < d["rooms"][0]:
        rooms = rooms or [(1, 1, lo, lo)]
    centre = lambda rm: (rm[0] + rm[2] // 2, rm[1] + rm[3] // 2)
    rooms.sort(key=lambda rm: (rm[0], rm[1]))
    entrance = rooms[0]
    ex, ey = centre(entrance)
    rest = sorted(rooms[1:], key=lambda rm: (abs(centre(rm)[0] - ex) + abs(centre(rm)[1] - ey), rm))
    order = [entrance] + rest
    edges = []
    for i in range(1, len(order)):
        cx, cy = centre(order[i])
        j = min(range(i), key=lambda k: (abs(centre(order[k])[0] - cx) + abs(centre(order[k])[1] - cy), k))
        edges.append((j, i))
    loops = S.rng("loops")
    for i in range(2, len(order)):
        if loops.chance(d.get("loop_chance", 20)):
            j = loops.below(i - 1)
            if (j, i) not in edges:
                edges.append((j, i))
    grid = [[0] * W for _ in range(H)]
    for x, y, w, h in order:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                grid[yy][xx] = 1
    cor = S.rng("corridors")
    for a, b in edges:
        (x0, y0), (x1, y1) = centre(order[a]), centre(order[b])
        horizontal_first = cor.below(2) == 0
        pts = [(x0, y0), (x1, y0), (x1, y1)] if horizontal_first else [(x0, y0), (x0, y1), (x1, y1)]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            for xx in range(min(ax, bx), max(ax, bx) + 1):
                for yy in range(min(ay, by), max(ay, by) + 1):
                    grid[yy][xx] = 1
                    if d.get("corridor_width", 1) > 1 and yy + 1 < H and xx + 1 < W:
                        grid[yy + (1 if ax != bx else 0)][xx + (1 if ay != by else 0)] = 1
    kinds = d.get("kinds", ["hall"])
    labelled = []
    for i, rm in enumerate(order):
        kind = "entrance" if i == 0 else "boss" if i == len(order) - 1 else kinds[(i - 1) % len(kinds)]
        labelled.append({"x": rm[0], "y": rm[1], "w": rm[2], "h": rm[3], "kind": kind})
    return {"grid": grid, "rooms": labelled, "edges": edges}


def generate(tf, seed: int, overrides=None) -> Sprite:
    return generate_frames(tf, seed, overrides)[0]


def generate_frames(tf, seed: int, overrides=None) -> list[Sprite]:
    from ..typefile import load
    from ..tiles import autotile
    lay = layout(tf, seed, overrides)
    terrain = load(tf.data["terrain"])
    sheet, _ = autotile.build_tileset(terrain, seed)
    img = autotile.render_map(sheet, terrain.data["tile"], autotile.map_tiles(lay["grid"]))
    void = img.color_index(hex_to_rgba(tf.data["palette"]["void"]))
    mark = {k: img.color_index(hex_to_rgba(c)) for k, c in tf.data["palette"]["marks"].items()}
    T = terrain.data["tile"]
    for i in range(len(img.px)):
        if img.px[i] == 0:
            img.px[i] = void
    for rm in lay["rooms"]:
        if rm["kind"] in mark:
            cx, cy = (rm["x"] + rm["w"] // 2) * T + T // 2, (rm["y"] + rm["h"] // 2) * T + T // 2
            for dy in range(-T // 4, T // 4 + 1):
                for dx in range(-T // 4, T // 4 + 1):
                    if abs(dx) + abs(dy) <= T // 4:
                        img.set(cx + dx, cy + dy, mark[rm["kind"]])
    return [img]
