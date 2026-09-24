"""The indexed sprite — the one data structure everything produces.

Index 0 is always transparent. Pixel identity (for goldens, caches and
share codes) is the SHA-256 of size + palette + indices, so two sprites
are "the same" exactly when every pixel and palette entry agrees.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import png
from .rng import sha256

RGBA = tuple[int, int, int, int]
TRANSPARENT: RGBA = (0, 0, 0, 0)


def hex_to_rgba(s: str) -> RGBA:
    s = s.strip().lstrip("#")
    if len(s) == 6:
        s += "ff"
    if len(s) != 8 or any(c not in "0123456789abcdefABCDEF" for c in s):
        raise ValueError(f"not a colour: #{s}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))


def rgba_to_hex(c: RGBA) -> str:
    return "#%02x%02x%02x" % c[:3] + ("" if c[3] == 255 else "%02x" % c[3])


@dataclass
class Sprite:
    w: int
    h: int
    palette: list[RGBA] = field(default_factory=lambda: [TRANSPARENT])
    px: bytearray = field(default=None)  # type: ignore[assignment]

    def __post_init__(self):
        if self.px is None:
            self.px = bytearray(self.w * self.h)

    # -- pixel access -------------------------------------------------
    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return 0

    def set(self, x: int, y: int, i: int) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = i

    def color_index(self, c: RGBA) -> int:
        """Index of colour c, appending it if new. Transparent maps to 0."""
        if c[3] == 0:
            return 0
        if c in self.palette:
            return self.palette.index(c)
        self.palette.append(c)
        if len(self.palette) > 256:
            raise ValueError("sprite exceeds 256 colours")
        return len(self.palette) - 1

    def copy(self) -> "Sprite":
        return Sprite(self.w, self.h, list(self.palette), bytearray(self.px))

    # -- identity -----------------------------------------------------
    def pixel_hash(self) -> str:
        head = self.w.to_bytes(4, "little") + self.h.to_bytes(4, "little") + len(self.palette).to_bytes(4, "little")
        pal = b"".join(bytes(c) for c in self.palette)
        return sha256(head + pal + bytes(self.px)).hex()

    def used_colors(self) -> int:
        """Opaque colours actually present (palette may carry unused ramps)."""
        return len({i for i in self.px if i != 0})

    # -- conversion ---------------------------------------------------
    def rgba(self) -> bytes:
        out = bytearray()
        for i in self.px:
            out += bytes(self.palette[i])
        return bytes(out)

    def scaled(self, k: int) -> "Sprite":
        s = Sprite(self.w * k, self.h * k, list(self.palette))
        for y in range(s.h):
            row = (y // k) * self.w
            for x in range(s.w):
                s.px[y * s.w + x] = self.px[row + x // k]
        return s

    def png_bytes(self, scale: int = 1) -> bytes:
        s = self.scaled(scale) if scale > 1 else self
        return png.encode_indexed(s.w, s.h, bytes(s.px), s.palette)

    def save(self, path, scale: int = 1) -> None:
        from pathlib import Path
        Path(path).write_bytes(self.png_bytes(scale))

    @classmethod
    def from_rgba(cls, w: int, h: int, rgba: bytes, alpha_cut: int = 128) -> "Sprite":
        s = cls(w, h)
        for p in range(w * h):
            c = tuple(rgba[p * 4:p * 4 + 4])
            if c[3] < alpha_cut:
                continue
            s.px[p] = s.color_index((c[0], c[1], c[2], 255))
        return s

    @classmethod
    def load(cls, path) -> "Sprite":
        w, h, rgba = png.read(path)
        return cls.from_rgba(w, h, rgba)


def blit(dst: Sprite, src: Sprite, ox: int, oy: int) -> None:
    """Copy opaque pixels of src into dst, remapping palettes."""
    remap = [dst.color_index(c) if i else 0 for i, c in enumerate(src.palette)]
    for y in range(src.h):
        for x in range(src.w):
            i = src.px[y * src.w + x]
            if i:
                dst.set(ox + x, oy + y, remap[i])


def outline_pass(cells: list[list[int]], w: int, h: int, eight: bool = False) -> None:
    """cells: 0 empty, 1 body, 2 outline. Empty cells touching body become outline."""
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if eight:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    marks = []
    for y in range(h):
        for x in range(w):
            if cells[y][x] != 0:
                continue
            for dx, dy in nb:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and cells[ny][nx] == 1:
                    marks.append((x, y))
                    break
    for x, y in marks:
        cells[y][x] = 2
