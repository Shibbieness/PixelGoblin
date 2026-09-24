"""47-tile blob autotiling — table generated in code, tiles generated too.

8-neighbour bitmask (N=1 NE=2 E=4 SE=8 S=16 SW=32 W=64 NW=128). A diagonal
bit only matters when both of its side neighbours are present; clearing it
otherwise reduces 256 masks to exactly 47 shapes. The table is derived, never
typed, so "one wrong corner" bugs cannot exist in it.

Tile texture is keyed to the pixel position inside a tile, not to the tile,
so all 47 tiles share one texture and join seamlessly.
"""

from __future__ import annotations

from .. import ENGINE_MAJOR
from ..rng import M32, Streams, hash32, master_seed
from ..sprite import TRANSPARENT, Sprite, hex_to_rgba

N, NE, E, SE, S, SW, W, NW = 1, 2, 4, 8, 16, 32, 64, 128
DIAG = ((NE, N, E), (SE, S, E), (SW, S, W), (NW, N, W))
NEIGH = ((0, -1, N), (1, -1, NE), (1, 0, E), (1, 1, SE), (0, 1, S), (-1, 1, SW), (-1, 0, W), (-1, -1, NW))
COLS = 8


def reduce_mask(m: int) -> int:
    for d, a, b in DIAG:
        if not (m & a and m & b):
            m &= ~d
    return m & 0xFF


def blob_masks() -> list[int]:
    return sorted({reduce_mask(m) for m in range(256)})


def index_table() -> dict[int, int]:
    """raw 8-bit mask (0..255) -> tile index 0..46."""
    order = {m: i for i, m in enumerate(blob_masks())}
    return {m: order[reduce_mask(m)] for m in range(256)}


def _dist(mask: int, x: int, y: int, T: int):
    """Distance to the nearest missing side, and whether it is north-facing."""
    best, north = 99, False
    cands = []
    if not mask & N:
        cands.append((y, True))
    if not mask & S:
        cands.append((T - 1 - y, False))
    if not mask & W:
        cands.append((x, True))
    if not mask & E:
        cands.append((T - 1 - x, False))
    if mask & N and mask & E and not mask & NE:
        cands.append((max(y, T - 1 - x), True))
    if mask & N and mask & W and not mask & NW:
        cands.append((max(y, x), True))
    if mask & S and mask & E and not mask & SE:
        cands.append((max(T - 1 - y, T - 1 - x), False))
    if mask & S and mask & W and not mask & SW:
        cands.append((max(T - 1 - y, x), False))
    for d, nf in cands:
        if d < best:
            best, north = d, nf
    return best, north


def build_tileset(tf, seed: int, overrides=None) -> tuple[Sprite, list[int]]:
    data = tf.data
    S_ = Streams(master_seed(tf.type_hash, seed, ENGINE_MAJOR), overrides)
    T = data["tile"]
    fill = [hex_to_rgba(c) for c in data["palette"]["fill"]]
    pal = [TRANSPARENT, hex_to_rgba(data["palette"]["outline"]), hex_to_rgba(data["palette"]["highlight"])] + fill
    tex = S_.rng("texture").next()
    masks = blob_masks()
    rows = (len(masks) + COLS - 1) // COLS
    sheet = Sprite(COLS * T, rows * T, pal)
    nf = len(fill)
    mid = 3 + (nf - 1) // 2
    for ti, m in enumerate(masks):
        ox, oy = (ti % COLS) * T, (ti // COLS) * T
        for y in range(T):
            for x in range(T):
                d, north = _dist(m, x, y, T)
                if d == 0:
                    idx = 0
                elif d == 1:
                    idx = 1
                elif d == 2:
                    idx = 2 if north else 3
                else:
                    h = hash32(tex ^ ((x * 0x9E3779B1) & M32) ^ ((y * 0x85EBCA6B) & M32)) % 16
                    idx = min(3 + nf - 1, mid + 1) if h == 0 else (max(3, mid - 1) if h == 1 else mid)
                sheet.px[(oy + y) * sheet.w + ox + x] = idx
    return sheet, masks


def map_tiles(grid: list[list[int]], edge_present: bool = False) -> list[list[int]]:
    """0/1 terrain grid -> tile index per cell (-1 where empty)."""
    table = index_table()
    h, w = len(grid), len(grid[0])
    out = [[-1] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if not grid[y][x]:
                continue
            m = 0
            for dx, dy, bit in NEIGH:
                nx, ny = x + dx, y + dy
                inside = 0 <= nx < w and 0 <= ny < h
                if (inside and grid[ny][nx]) or (not inside and edge_present):
                    m |= bit
            out[y][x] = table[m]
    return out


def render_map(sheet: Sprite, T: int, tiles: list[list[int]]) -> Sprite:
    h, w = len(tiles), len(tiles[0])
    img = Sprite(w * T, h * T, list(sheet.palette))
    for ty in range(h):
        for tx in range(w):
            ti = tiles[ty][tx]
            if ti < 0:
                continue
            sx, sy = (ti % COLS) * T, (ti // COLS) * T
            for y in range(T):
                row = (sy + y) * sheet.w
                img.px[(ty * T + y) * img.w + tx * T:(ty * T + y) * img.w + tx * T + T] = sheet.px[row + sx:row + sx + T]
    return img
