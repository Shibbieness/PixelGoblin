"""Built-in palettes, plus .hex / .gpl import.

Each palette records where its colours came from. PICO-8's 16 colours are a
widely reproduced list of values; the others here are original to
PixelGoblin (AGPL like the engine).
"""

from __future__ import annotations

from pathlib import Path

from .sprite import hex_to_rgba

BUILTIN: dict[str, dict] = {
    "pico8": {
        "source": "PICO-8 fantasy console default palette (Lexaloffle); colour values widely reproduced",
        "colors": ["#000000", "#1d2b53", "#7e2553", "#008751", "#ab5236", "#5f574f", "#c2c3c7", "#fff1e8",
                   "#ff004d", "#ffa300", "#ffec27", "#00e436", "#29adff", "#83769c", "#ff77a8", "#ffccaa"],
    },
    "gameboy": {
        "source": "four-shade green, original values for PixelGoblin",
        "colors": ["#0f1f0f", "#305030", "#8aa050", "#d0e0a0"],
    },
    "goblin16": {
        "source": "original to PixelGoblin",
        "colors": ["#14101c", "#2b2238", "#4a3a4f", "#6e5a5a", "#3b5a2a", "#5f8a36", "#9cc251", "#d8e89a",
                   "#5a2a1e", "#9a4a28", "#d68a3a", "#f2c96b", "#1e3a5a", "#2f6f8a", "#6ab7c2", "#e8f2e0"],
    },
}


def get(name: str) -> list[tuple[int, int, int, int]]:
    if name not in BUILTIN:
        raise KeyError(f"unknown palette {name!r}; built-ins are {sorted(BUILTIN)} (or pass a .hex/.gpl file path)")
    return [hex_to_rgba(c) for c in BUILTIN[name]["colors"]]


def load_file(path: str | Path) -> list[tuple[int, int, int, int]]:
    """Lospec-style .hex (one RRGGBB per line) or GIMP .gpl."""
    p = Path(path)
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if p.suffix == ".gpl":
            parts = line.split()
            if len(parts) >= 3 and all(x.isdigit() for x in parts[:3]):
                out.append((int(parts[0]), int(parts[1]), int(parts[2]), 255))
        else:
            h = line.lstrip("#")
            if len(h) == 6 and all(c in "0123456789abcdefABCDEF" for c in h):
                out.append(hex_to_rgba(h))
    if not out:
        raise ValueError(f"no colours found in {p}")
    return out


def resolve(spec: str) -> list[tuple[int, int, int, int]]:
    if spec in BUILTIN:
        return get(spec)
    return load_file(spec)
