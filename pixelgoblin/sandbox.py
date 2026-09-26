"""Goblin Grounds: a small sandbox world built from the resource packs.

A world is a grid of tiles (ground, water, rock) with things placed on it: plants
and trees to look at, fungi and ores to gather, animals that wander, a crafting
station, and a start point. It is planned from a biome's residents (the biomes
pack lists which flora, fungi, fauna and ores live where) and a seed, and every
gatherable thing is guaranteed reachable from the start.

Weights come from CRUCIBLE through the ores pack: a chunk of iron ore weighs what
500 cm3 of iron weighs. A goblin carries up to CARRY_GRAMS and slows as the load
grows, so heavy ore is a real choice. Fantasy materials keep their authored weight
(CRUCIBLE's intentionally_ungrounded rule).

`plan_world`, `reachable`, `quests` and `speed` are written in the transpiler's
integer subset, so the minigame page plans exactly the same world (gate B23).

    —Shibbieness
    —Claude
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

T_GROUND = 0
T_WATER = 1
T_ROCK = 2
CARRY_GRAMS = 12000            # what a goblin can carry, in grams
FUNGUS_GRAMS = 150             # authored: CRUCIBLE has no mushrooms
FLOWER_GRAMS = 40
TILE = 16
STATION_TIERS = ["IMPROVISED", "BASIC", "STANDARD", "MASTERWORK", "LEGENDARY"]


def _disc(grid, w, h, cx, cy, r, kind):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if x >= 1 and x < w - 1 and y >= 1 and y < h - 1 and (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r + r:
                grid[y * w + x] = kind


def reachable(grid, w, h, sx, sy):
    """Flood fill over ground from the start: 1 where a goblin can walk."""
    seen = bytearray(w * h)
    if grid[sy * w + sx] != 0:
        return seen
    queue = [sy * w + sx]
    seen[sy * w + sx] = 1
    head = 0
    while head < len(queue):
        i = queue[head]
        head += 1
        x = i % w
        y = i // w
        for d in range(4):
            nx = x + [1, -1, 0, 0][d]
            ny = y + [0, 0, 1, -1][d]
            if nx >= 0 and nx < w and ny >= 0 and ny < h:
                j = ny * w + nx
                if seen[j] == 0 and grid[j] == 0:
                    seen[j] = 1
                    queue.append(j)
    return seen


def plan_world(cfg, rng):
    """cfg: w, h, water (percent), rock (percent), and lists of type ids:
    flora, fungi, ores, fauna. Returns tiles, things, start and station."""
    w = cfg["w"]
    h = cfg["h"]
    grid = bytearray(w * h)
    for x in range(w):
        grid[x] = T_ROCK
        grid[(h - 1) * w + x] = T_ROCK
    for y in range(h):
        grid[y * w] = T_ROCK
        grid[y * w + w - 1] = T_ROCK
    ponds = cfg["water"] * w * h // 1600
    for k in range(ponds):
        _disc(grid, w, h, 2 + rng.below(w - 4), 2 + rng.below(h - 4), 1 + rng.below(3), T_WATER)
    crags = cfg["rock"] * w * h // 1600
    for k in range(crags):
        _disc(grid, w, h, 2 + rng.below(w - 4), 2 + rng.below(h - 4), rng.below(3), T_ROCK)
    sx = w // 2
    sy = h // 2
    _disc(grid, w, h, sx, sy, 2, T_GROUND)
    seen = reachable(grid, w, h, sx, sy)
    open_cells = []
    for i in range(w * h):
        if seen[i] == 1 and abs(i % w - sx) + abs(i // w - sy) > 2:
            open_cells.append(i)
    things = []
    kinds = ["flora", "fungi", "ores", "fauna"]
    counts = cfg["counts"]
    for kind in kinds:
        pool = cfg[kind]
        if len(pool) == 0:
            continue
        for k in range(counts[kind]):
            if len(open_cells) == 0:
                break
            j = rng.below(len(open_cells))
            cell = open_cells[j]
            open_cells[j] = open_cells[len(open_cells) - 1]
            open_cells.pop()
            if kind == "ores":
                near_rock = 0
                x = cell % w
                y = cell // w
                for d in range(4):
                    nb = (y + [0, 0, 1, -1][d]) * w + x + [1, -1, 0, 0][d]
                    if grid[nb] == T_ROCK:
                        near_rock = 1
                if near_rock == 0 and rng.below(3) > 0 and len(open_cells) > 0:
                    j = rng.below(len(open_cells))
                    swap = open_cells[j]
                    open_cells[j] = cell
                    cell = swap
            things.append({"kind": kind, "type": pool[rng.below(len(pool))], "x": cell % w, "y": cell // w,
                           "gather": 1 if kind == "fungi" or kind == "ores" else 0, "seed": rng.below(1000)})
    return {"w": w, "h": h, "tiles": list(grid), "things": things, "start": [sx, sy], "station": [sx + 1, sy - 1]}


def quests(plan, rng, n):
    """Up to n deliveries of things that exist on the map, never more than are there."""
    have = {}
    order = []
    for t in plan["things"]:
        if t["gather"] == 1:
            if have.get(t["type"], None) is None:
                have[t["type"]] = 0
                order.append(t["type"])
            have[t["type"]] = have[t["type"]] + 1
    out = []
    for k in range(n):
        if len(order) == 0:
            break
        j = rng.below(len(order))
        tid = order[j]
        order[j] = order[len(order) - 1]
        order.pop()
        out.append({"type": tid, "count": 1 + rng.below(have[tid])})
    return out


def speed(load_grams, carry_grams):
    """Walking speed in percent: 100 empty, 50 fully loaded, and no further when overloaded."""
    if load_grams >= carry_grams:
        return 50
    return 100 - 50 * load_grams // carry_grams


# ---------------------------------------------------------------- Python side: config, weights, map, export
def _biomes_pack() -> dict:
    from . import typefile
    for p in typefile.packs():
        if p.get("id") == "boc.pack.biomes":
            return p
    raise ValueError("the biomes pack is not installed (flavors/boc/packs/biomes/pack.toml)")


def config(biome: str, w: int = 28, h: int = 18) -> dict:
    res = _biomes_pack().get("residents", {}).get(biome)
    if res is None:
        raise ValueError(f"no biome called {biome!r}; biomes: {sorted(_biomes_pack().get('residents', {}))}")
    pick = lambda pre: [t for t in res if t.startswith(pre)]
    return {"biome": biome, "w": w, "h": h, "water": 10 if biome not in ("coast", "swamp", "underwater") else 22, "rock": 12 if biome not in ("mountain", "badlands") else 24,
            "flora": pick("boc.flora."), "fungi": pick("boc.fungus."), "ores": pick("boc.ore."), "fauna": pick("boc.fauna.") + pick("boc.fish."),
            "counts": {"flora": w * h // 18, "fungi": w * h // 60, "ores": w * h // 50, "fauna": w * h // 120}}


def config_hash(cfg: dict) -> str:
    """The world's identity: its config, canonical JSON. The same hash in JavaScript."""
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def world(biome: str, seed: int, w: int = 28, h: int = 18) -> dict:
    from . import ENGINE_MAJOR
    from .rng import Streams, master_seed
    cfg = config(biome, w, h)
    S = Streams(master_seed(config_hash(cfg), seed, ENGINE_MAJOR))
    plan = plan_world(cfg, S.rng("world"))
    plan["quests"] = quests(plan, S.rng("quests"), 3)
    plan["biome"] = biome
    plan["seed"] = seed
    plan["config_hash"] = config_hash(cfg)
    return plan


def grams(type_id: str) -> tuple[int, str]:
    """What one gathered thing weighs, and where the number came from."""
    from . import typefile
    tf = typefile.load(type_id)
    cr = tf.data.get("crucible")
    if cr:
        return cr["chunk_grams"], cr["grounding"]
    if type_id.startswith("boc.fungus."):
        return FUNGUS_GRAMS, "authored"
    return FLOWER_GRAMS, "authored"


def render(plan: dict, scale: int = 1):
    """A preview of the world: ground, water and rock, then everything on it, back to front."""
    from . import gen, typefile
    from .sprite import TRANSPARENT, Sprite, blit, hex_to_rgba
    from .rng import Rng, derive, master_seed
    biome = plan["biome"]
    ground = typefile.load(f"boc.biome.{biome}.ground").data["palette"]
    sky = typefile.load(f"boc.biome.{biome}.sky").data["palette"]["sky"]
    W, H = plan["w"] * TILE, plan["h"] * TILE
    pal = [TRANSPARENT] + [hex_to_rgba(c) for c in ground["fill"]] + [hex_to_rgba(c) for c in (sky[1:4] if biome == "underwater" else ("#24507a", "#2e6494", "#4a86b4"))] + [hex_to_rgba(c) for c in ("#3a3a40", "#5a5a64", "#7a7a86", "#9a9aa6")]
    g0, w0, r0 = 1, 1 + len(ground["fill"]), 1 + len(ground["fill"]) + 3
    out = Sprite(W, H, pal)
    rng = Rng(derive(master_seed(plan["config_hash"], plan["seed"], 0), "texture"))
    for ty in range(plan["h"]):
        for tx in range(plan["w"]):
            k = plan["tiles"][ty * plan["w"] + tx]
            for y in range(TILE):
                for x in range(TILE):
                    n = rng.below(16)
                    if k == T_GROUND:
                        c = g0 + (1 if n < 13 else 2 if n < 15 else 0)
                    elif k == T_WATER:
                        c = w0 + (1 if n < 13 else 2)
                    else:
                        c = r0 + (1 if (x + y) % 7 else 0) + (1 if y < 3 else 0)
                    out.px[(ty * TILE + y) * W + tx * TILE + x] = c
    placed = sorted(plan["things"], key=lambda t: (t["y"], t["x"]))
    for t in placed:
        spr = gen.frames(typefile.load(t["type"]), t["seed"])[0]
        blit(out, spr, t["x"] * TILE + TILE // 2 - spr.w // 2, t["y"] * TILE + TILE - spr.h)
    return out.scaled(scale) if scale > 1 else out


def export(plan: dict, out_dir: Path) -> list[Path]:
    """world.json (for game engines), map.png (preview), atlas.png + atlas.json (every sprite used)."""
    from . import gen, typefile
    from .sprite import Sprite, TRANSPARENT, blit
    out_dir.mkdir(parents=True, exist_ok=True)
    types = sorted({t["type"] for t in plan["things"]})
    sprites = [(tid, gen.frames(typefile.load(tid), 1)[0]) for tid in types]
    cell = max(max(s.w, s.h) for _, s in sprites) if sprites else 16
    cols = 12
    rows = (len(sprites) + cols - 1) // cols
    atlas = Sprite(cols * cell, max(1, rows) * cell, [TRANSPARENT])
    frames = {}
    for i, (tid, s) in enumerate(sprites):
        x, y = (i % cols) * cell, (i // cols) * cell
        for p, c in enumerate(s.palette):
            if p and c not in atlas.palette:
                atlas.palette.append(c)
        remap = [0] + [atlas.palette.index(c) for c in s.palette[1:]]
        for yy in range(s.h):
            for xx in range(s.w):
                v = s.px[yy * s.w + xx]
                if v:
                    atlas.px[(y + yy) * atlas.w + x + xx] = remap[v]
        g, src = grams(tid)
        frames[tid] = {"x": x, "y": y, "w": s.w, "h": s.h, "grams": g, "weight_source": src, "label": typefile.load(tid).data.get("label", tid)}
    world_json = dict(plan, tile=TILE, carry_grams=CARRY_GRAMS, station_tiers=STATION_TIERS, atlas="atlas.png", sprites=frames,
                      tiles_legend={"0": "ground", "1": "water", "2": "rock"})
    paths = [out_dir / "world.json", out_dir / "atlas.png", out_dir / "map.png"]
    paths[0].write_text(json.dumps(world_json, indent=1))
    atlas.save(paths[1])
    render(plan).save(paths[2])
    return paths
