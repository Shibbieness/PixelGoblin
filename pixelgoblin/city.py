"""City — a whole population from a list of names.

    Grubnak Ashfang
    Mizzle Ashfang
    Tok Ashfang
    Old Pell : elder_scholar
    Nib Reedwhistle (child)

Every citizen is decided by their own name and the city file, nothing else:
  * the name is the seed (rng.seed_from_name), so Grubnak always looks the same;
  * the role comes from the city's census weights, drawn from the person's own
    stream; `: role` in the list pins it; `(child)` or `(elder)` picks from
    those lists;
  * a surname is a household: the first two grown members are the parents,
    later members are their children, who inherit face, hair and build from
    them (brood's rule: whole streams, a few mutations);
  * a household shares a subspecies and, if the city has clans, clan colours.

Adding a name never changes anyone else, except that a new member of a
household becomes that household's newest child. Gate B19 checks both.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from . import ENGINE_MAJOR
from .rng import Streams, master_seed, seed_from_name, sha256

SCHEMA = "pixelgoblin/city@1"
INHERITED = ("g/body", "g/face", "g/hair")


def load_city(path_or_id: str) -> dict:
    from .typefile import REPO, search_path
    p = Path(path_or_id)
    if not p.exists():
        for root in search_path():
            for q in sorted(Path(root).rglob("*.city.toml")):
                d = tomllib.loads(q.read_text())
                if d.get("id") == path_or_id:
                    p = q
                    break
    if not p.exists():
        raise FileNotFoundError(f"no city file or id {path_or_id!r}")
    d = tomllib.loads(p.read_text())
    if d.get("schema") != SCHEMA:
        raise ValueError(f"{p}: `schema` must be {SCHEMA!r}")
    d["_hash"] = sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hex()
    return d


def parse_names(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        role = None
        tag = None
        if ":" in line:
            line, role = [x.strip() for x in line.split(":", 1)]
        m = re.search(r"\((child|elder|adult)\)\s*$", line)
        if m:
            tag = m.group(1)
            line = line[:m.start()].strip()
        name = " ".join(line.split())
        words = name.split(" ")
        out.append({"name": name, "household": words[-1] if len(words) > 1 else name, "role": role, "tag": tag})
    return out


def _weighted(rng, table: dict) -> str:
    keys = sorted(table)
    return keys[rng.weighted([table[k] for k in keys])]


def sub_id(sub: str) -> str:
    """A city's [subspecies] key: a goblin subspecies by short name (`snow`), or any
    overlay by full id (`"boc.race.sub.dwarf"`), so a city can hold other folk."""
    return sub if "." in sub else f"boc.goblin.sub.{sub}"


def census(city: dict, names: list[dict]) -> list[dict]:
    """Everyone in the city: name, seed, role, subspecies, clan, household,
    parents, band in the village scene, and stream overrides for children."""
    from .gen import rig
    from .typefile import load
    from . import typefile
    ns = city.get("role_prefix", "boc.goblin.")
    houses: dict = {}
    people = []
    for n in names:
        seed = seed_from_name(n["name"])
        S = Streams(master_seed(city["_hash"], seed, ENGINE_MAJOR))
        house = houses.setdefault(n["household"], [])
        H = Streams(master_seed(city["_hash"], seed_from_name("house:" + n["household"]), ENGINE_MAJOR))
        grown = [p for p in house if p["age_group"] != "child"]
        tag = n["tag"] or ("child" if len(grown) >= 2 else "adult")
        if n["role"]:
            role = n["role"]
        elif tag == "child":
            role = _weighted(S.rng("city/role"), city.get("children", {"child_boy": 1, "child_girl": 1}))
        elif tag == "elder":
            role = _weighted(S.rng("city/role"), city.get("elders", {"elder": 1}))
        else:
            role = _weighted(S.rng("city/role"), city["census"])
        sub = _weighted(H.rng("city/sub"), city.get("subspecies", {"common": 1}))
        clans = city.get("clans", [])
        team = clans[H.rng("city/clan").below(len(clans))] if clans else None
        for c in clans:  # a household named after a clan belongs to it
            if c.lower() == n["household"].lower():
                team = c
        bands = city.get("bands", {"far": 3, "mid": 4, "near": 1})
        p = {"name": n["name"], "seed": seed, "role": ns + role if "." not in role else role, "sub": None if sub == "common" else sub,
             "team": team, "household": n["household"], "age_group": tag, "parents": [],
             "band": _weighted(S.rng("city/band"), bands)}
        if tag == "child" and len(grown) >= 2:
            pa, pb = grown[0], grown[1]
            p["parents"] = [pa["name"], pb["name"]]
            pick = S.rng("city/inherit")
            over, record = {}, {}
            for path in INHERITED:
                r = pick.below(100)
                if r < 10:
                    record[path] = "mutation"
                    continue
                src = pa if r % 2 == 0 else pb
                over[path] = _streams(src).seed(path)
                record[path] = src["name"]
            p["overrides"] = over
            p["inherited"] = record
        house.append(p)
        people.append(p)
    return people


def _type(p):
    from .typefile import compose, load, with_team
    tf = compose(p["role"], sub_id(p["sub"])) if p["sub"] else load(p["role"])
    return with_team(tf, p["team"]) if p["team"] else tf


def _streams(p):
    from .gen import rig
    return rig.streams_for(_type(p), p["seed"], p.get("overrides"))


def sprite(p, tier=64, era=None):
    from .gen import rig
    tf = _type(p)
    g = rig.genome(tf.data, rig.streams_for(tf, p["seed"], p.get("overrides")))
    return rig.render(tf.data, g, tier, era)[0]


def village(city: dict, people: list[dict], seed: int = 0):
    """The city's scene, peopled by its census (up to each band's count; the
    rest are indoors, and the census says so)."""
    from .gen import scene
    from .typefile import load
    sc = load(city["scene"])
    cap = {b["name"]: b["count"] for b in sc.data["crowd"]}
    shown = []
    for p in people:
        if cap.get(p["band"], 0) > 0:
            cap[p["band"]] -= 1
            shown.append({"role": p["role"], "seed": p["seed"], "band": p["band"], "overrides": p.get("overrides"),
                          "sub": sub_id(p["sub"]) if p["sub"] else None, "team": p["team"]})
            p["outdoors"] = True
        else:
            p["outdoors"] = False
    return scene.generate_frames(sc, seed, population=shown)[0]


def public(people: list[dict]) -> list[dict]:
    """The census without stream bytes (for JSON)."""
    return [{k: v for k, v in p.items() if k != "overrides"} for p in people]
