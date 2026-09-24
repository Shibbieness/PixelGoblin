"""Generative type data files: load, inherit, validate, hash.

Authors write TOML. The engine resolves `extends`, validates, and hashes the
resolved content as canonical JSON (sorted keys, no whitespace), so
whitespace and comment edits never change a sprite and value edits always do
(ADR-005). Floats are refused anywhere in a type file: runtime generation is
integer-only (ADR-002), and a float would also serialise differently across
language ports.

Every error is written in plain English with the field path, because the
person reading it may be tired, dyslexic, or both.
"""

from __future__ import annotations

import difflib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .rng import sha256
from .sprite import hex_to_rgba

SCHEMA = "pixelgoblin/type@1"
GENERATORS = ("mask", "lsystem", "parallax", "autotile", "uikit")
MASK_CHARS = set(".12#")
REPO = Path(__file__).resolve().parent.parent


class TypeFileError(ValueError):
    def __init__(self, problems: list[str], source: str = ""):
        self.problems = problems
        self.source = source
        head = f"{source}: " if source else ""
        super().__init__(head + "; ".join(problems))


@dataclass(frozen=True)
class TypeFile:
    data: dict
    type_hash: str
    source: str

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def generator(self) -> str:
        return self.data["generator"]

    @property
    def license(self) -> str:
        return self.data["license"]


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def type_hash(data: dict) -> str:
    return sha256(canonical_json(data).encode("utf-8")).hex()


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def search_path() -> list[Path]:
    return [REPO / "types" / "vanilla", REPO / "flavors"]


def find_by_id(type_id: str, extra: list[Path] | None = None) -> Path:
    for root in (extra or []) + search_path():
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.toml")):
            if p.name == "tags.toml":
                continue
            try:
                if tomllib.loads(p.read_text()).get("id") == type_id:
                    return p
            except tomllib.TOMLDecodeError:
                continue
    raise TypeFileError([f"no type file with id {type_id!r} on the search path"])


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise TypeFileError([f"this is not valid TOML — {e}"], str(path)) from None


def resolve_raw(path: Path, seen: tuple = ()) -> dict:
    raw = _read_toml(path)
    parent = raw.pop("extends", None)
    if parent is None:
        return raw
    if parent in seen:
        raise TypeFileError([f"`extends` loops back to {parent!r}"], str(path))
    base_path = find_by_id(parent, [path.parent])
    return _merge(resolve_raw(base_path, seen + (raw.get("id"),)), raw)


def from_dict(data: dict, source: str = "<dict>") -> TypeFile:
    problems = validate(data)
    if problems:
        raise TypeFileError(problems, source)
    return TypeFile(data, type_hash(data), source)


def load(path: str | Path) -> TypeFile:
    p = Path(path)
    if not p.exists():
        try:
            p = find_by_id(str(path))
        except TypeFileError:
            raise TypeFileError([f"no such file, and no type with that id: {path}"]) from None
    return from_dict(resolve_raw(p), str(p))


# ---------------------------------------------------------------- validation

def _floats(obj, path="") -> list[str]:
    out = []
    if isinstance(obj, float):
        out.append(f"`{path}` is a decimal number ({obj}); type files use whole numbers only so every platform generates the same pixels")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out += _floats(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _floats(v, f"{path}[{i}]")
    return out


class _V:
    def __init__(self, data):
        self.d = data
        self.p: list[str] = []

    def get(self, dotted, kind, required=True):
        cur = self.d
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                if required:
                    self.p.append(f"`{dotted}` is missing")
                return None
            cur = cur[part]
        if kind is not None and not isinstance(cur, kind) or (kind is int and isinstance(cur, bool)):
            names = kind.__name__ if isinstance(kind, type) else "/".join(k.__name__ for k in kind)
            word = {"int": "a whole number", "str": "text", "list": "a list", "dict": "a table", "bool": "true or false"}.get(names, names)
            self.p.append(f"`{dotted}` should be {word}, but it is {type(cur).__name__}")
            return None
        return cur

    def int_range(self, dotted, lo, hi, required=True):
        v = self.get(dotted, int, required)
        if v is not None and not lo <= v <= hi:
            self.p.append(f"`{dotted}` is {v}; it must be between {lo} and {hi}")
        return v

    def color(self, dotted, value=None, required=True):
        v = value if value is not None else self.get(dotted, str, required)
        if v is None:
            return None
        try:
            hex_to_rgba(v)
        except ValueError:
            self.p.append(f"`{dotted}` is {v!r}; colours are written like \"#3a5f2b\"")
        return v

    def colors(self, dotted, lo, hi, required=True):
        v = self.get(dotted, list, required)
        if v is None:
            return None
        if not lo <= len(v) <= hi:
            self.p.append(f"`{dotted}` has {len(v)} colours; it needs {lo} to {hi}, ordered dark to light")
        for i, c in enumerate(v):
            if not isinstance(c, str):
                self.p.append(f"`{dotted}[{i}]` should be a colour like \"#3a5f2b\"")
            else:
                self.color(f"{dotted}[{i}]", c)
        return v

    def template(self, dotted, required=True):
        t = self.get(dotted, list, required)
        if t is None:
            return None
        if not t or not all(isinstance(r, str) for r in t):
            self.p.append(f"`{dotted}` must be a list of text rows like \"..12#\"")
            return None
        if len({len(r) for r in t}) != 1:
            self.p.append(f"`{dotted}` rows have different lengths {sorted({len(r) for r in t})}; every row must be the same width")
        bad = sorted({c for r in t for c in r} - MASK_CHARS)
        if bad:
            self.p.append(f"`{dotted}` uses {bad}; only . (empty) 1 (maybe body) 2 (body or edge) # (always body) are allowed")
        return t


def validate(data: dict) -> list[str]:
    v = _V(data)
    v.p += _floats(data)
    if data.get("schema") != SCHEMA:
        v.p.append(f"`schema` must be \"{SCHEMA}\" (found {data.get('schema')!r})")
    tid = v.get("id", str)
    if tid is not None and (not tid or " " in tid):
        v.p.append("`id` must be dotted text with no spaces, like \"vanilla.creature.blob\"")
    tag = v.get("tag", str)
    if tag is not None:
        _check_tag(tag, v.p)
    lic = v.get("license", str)
    if lic is not None and not lic.strip():
        v.p.append("`license` is blank; every type file must say what license its sprites carry (whitespace is not a license)")
    gen = v.get("generator", str)
    if gen is not None and gen not in GENERATORS:
        near = difflib.get_close_matches(gen, GENERATORS, 1)
        v.p.append(f"`generator` {gen!r} is not known" + (f" — did you mean {near[0]!r}?" if near else f"; choose one of {list(GENERATORS)}"))
    size = v.get("size", list)
    W = H = None
    if size is not None:
        if len(size) != 2 or not all(isinstance(n, int) and not isinstance(n, bool) for n in size):
            v.p.append("`size` must be two whole numbers, like [16, 16]")
        elif not all(4 <= n <= 512 for n in size):
            v.p.append(f"`size` {size} must be between 4 and 512 on each side")
        else:
            W, H = size
    if gen == "mask":
        _validate_mask(v, W, H)
    elif gen == "lsystem":
        _validate_lsystem(v)
    elif gen == "parallax":
        _validate_parallax(v)
    elif gen == "autotile":
        v.int_range("tile", 8, 32)
        v.colors("palette.fill", 3, 8)
        v.color("palette.outline")
        v.color("palette.highlight")
    elif gen == "uikit":
        v.int_range("tile", 6, 32)
        v.int_range("border", 1, 3)
        corner = v.get("corner", str)
        if corner is not None and corner not in ("square", "round", "notch"):
            v.p.append(f"`corner` {corner!r} must be square, round or notch")
        v.colors("palette.material", 4, 8)
        v.color("palette.outline")
        v.int_range("icons", 0, 16, required=False)
    return v.p


def _validate_mask(v: _V, W, H):
    v.color("palette.outline")
    style = v.get("outline_style", str, required=False)
    if style is not None and style not in ("plain", "selout"):
        v.p.append(f"`outline_style` {style!r} must be plain or selout")
    ramps = v.get("palette.ramps", list)
    names = set()
    for i, r in enumerate(ramps or []):
        if not isinstance(r, dict):
            v.p.append(f"`palette.ramps[{i}]` must be a table with name, weight and colors")
            continue
        sub = _V(r)
        n = sub.get("name", str)
        sub.int_range("weight", 0, 1000)
        sub.colors("colors", 2, 8)
        v.p += [f"palette.ramps[{i}]: {m}" for m in sub.p]
        if n:
            if n in names:
                v.p.append(f"two ramps are named {n!r}")
            names.add(n)
    if ramps is not None and not ramps:
        v.p.append("`palette.ramps` is empty; add at least one ramp of colours")
    elif ramps and all(isinstance(r, dict) and isinstance(r.get("weight"), int) for r in ramps) and sum(r["weight"] for r in ramps) == 0:
        v.p.append("every ramp has weight 0, so `ramp = \"any\"` has nothing to pick; give at least one ramp a weight above 0")
    mirror = v.get("mirror", bool, required=False)
    v.int_range("features.eyes", 0, 2, required=False)
    if isinstance(v.d.get("features"), dict) and "eye_color" in v.d["features"]:
        v.color("features.eye_color")
    band = v.get("features.eye_band", list, required=False)
    if band is not None and (len(band) != 2 or not all(isinstance(b, int) for b in band) or not 0 <= band[0] <= band[1] <= 100):
        v.p.append("`features.eye_band` must be [top, bottom] percentages of the body height, like [10, 30]")
    v.int_range("animation.frames", 1, 8, required=False)
    v.int_range("animation.frame_ms", 16, 2000, required=False)
    layers = [("body", v.d.get("body"))] + [(f"parts[{i}]", p) for i, p in enumerate(v.d.get("parts", []) or [])]
    seen = set()
    for label, layer in layers:
        if layer is None:
            v.p.append("`body` is missing — it holds the main template")
            continue
        if not isinstance(layer, dict):
            v.p.append(f"`{label}` must be a table")
            continue
        sub = _V(layer)
        t = sub.template("template")
        anchor = sub.get("anchor", list)
        ramp = sub.get("ramp", str, required=False)
        if label != "body":
            nm = sub.get("name", str)
            sub.int_range("chance", 0, 100)
            if nm in seen:
                sub.p.append(f"part name {nm!r} is used twice; part names must be unique (each owns its own random stream)")
            seen.add(nm)
        if ramp is not None and ramp != "any" and ramp not in names:
            near = difflib.get_close_matches(ramp, sorted(names), 1)
            sub.p.append(f"`ramp` {ramp!r} is not one of the palette ramps" + (f" — did you mean {near[0]!r}?" if near else ""))
        if t and anchor and W and len(anchor) == 2:
            fw = len(t[0]) * (2 if mirror else 1)
            ax, ay = anchor
            if ax < 1 or ay < 1 or ax + fw > W - 1 or ay + len(t) > H - 1:
                sub.p.append(f"template ({fw}x{len(t)} at {anchor}) does not fit inside size {W}x{H} with a 1-pixel border for the outline")
        v.p += [f"{label}: {m}" for m in sub.p]


def _validate_lsystem(v: _V):
    axiom = v.get("axiom", str)
    rules = v.get("rules", dict)
    v.int_range("iterations", 1, 6)
    step = v.get("step", list)
    if step is not None and (len(step) != 2 or not all(isinstance(s, int) for s in step) or not 1 <= step[0] <= step[1] <= 16):
        v.p.append("`step` must be [min, max] pixel lengths, 1 to 16, min not above max")
    v.colors("palette.bark", 2, 6)
    v.colors("palette.leaf", 2, 6)
    v.color("palette.outline")
    v.color("palette.fruit")
    v.int_range("leaf_radius", 0, 3)
    v.int_range("fruit_chance", 0, 100)
    v.int_range("trunk_width", 1, 2)
    for sym, opts in (rules or {}).items():
        if len(sym) != 1:
            v.p.append(f"rule key {sym!r} must be a single symbol")
        if not isinstance(opts, list) or not opts:
            v.p.append(f"`rules.{sym}` must be a list of {{to, weight}} options")
            continue
        for i, o in enumerate(opts):
            if not isinstance(o, dict) or not isinstance(o.get("to"), str) or not isinstance(o.get("weight"), int) or o["weight"] < 1:
                v.p.append(f"`rules.{sym}[{i}]` needs text `to` and a whole-number `weight` of 1 or more")
    if axiom is not None and rules is not None and not v.p:
        # worst case growth check keeps generation bounded
        n = len(axiom)
        grow = max((len(o["to"]) for opts in rules.values() for o in opts), default=1)
        for _ in range(v.d.get("iterations", 1)):
            n *= max(1, grow)
        if n > 200000:
            v.p.append(f"rules could grow to about {n} symbols; reduce iterations or rule length (limit 200000)")


def _validate_parallax(v: _V):
    v.colors("palette.sky", 2, 8)
    v.int_range("stars", 0, 400, required=False)
    layers = v.get("layers", list)
    for i, L in enumerate(layers or []):
        if not isinstance(L, dict):
            v.p.append(f"`layers[{i}]` must be a table")
            continue
        sub = _V(L)
        sub.get("name", str)
        sub.colors("colors", 2, 6)
        sub.int_range("base", 0, 100)
        sub.int_range("scroll", 0, 100)
        periods = sub.get("periods", list)
        amps = sub.get("amps", list)
        if periods is not None and amps is not None:
            if len(periods) != len(amps) or not periods:
                sub.p.append("`periods` and `amps` must be lists of the same length (one entry per noise octave)")
            elif not all(isinstance(x, int) and x >= 2 for x in periods) or not all(isinstance(x, int) and x >= 0 for x in amps):
                sub.p.append("`periods` must be whole numbers of 2 or more, `amps` whole numbers of 0 or more")
        v.p += [f"layers[{i}]: {m}" for m in sub.p]
    if layers is not None and not layers:
        v.p.append("`layers` is empty; add at least one landscape layer")


# ---------------------------------------------------------------- tags

def taxonomy() -> dict:
    p = REPO / "types" / "tags.toml"
    return tomllib.loads(p.read_text()) if p.exists() else {"roots": {}, "tag": {}}


def _check_tag(tag: str, problems: list[str]) -> None:
    roots = sorted(taxonomy().get("roots", {}))
    root = tag.split(".")[0]
    if roots and root not in roots:
        near = difflib.get_close_matches(root, roots, 1)
        problems.append(f"tag root {root!r} is not in types/tags.toml" + (f" — did you mean {near[0]!r}?" if near else f"; known roots: {roots}"))


def profile_for(tag: str) -> dict:
    """Conversion profile for a tag, inheriting from each dotted parent."""
    tax = taxonomy()
    profiles = tax.get("tag", {})
    parts = tag.split(".")
    prof: dict = dict(tax.get("default", {}))
    found = False
    for i in range(1, len(parts) + 1):
        key = ".".join(parts[:i])
        if key in profiles:
            prof = _merge(prof, profiles[key])
            found = True
    if not found and parts[0] not in tax.get("roots", {}):
        known = sorted(tax.get("roots", {}))
        near = difflib.get_close_matches(parts[0], known, 1)
        raise TypeFileError([f"unknown tag {tag!r}" + (f" — did you mean {near[0]!r}?" if near else f"; known roots: {known}")])
    return prof
