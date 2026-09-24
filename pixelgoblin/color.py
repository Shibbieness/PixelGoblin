"""Colour maths for TOOL-TIME work only (conversion, analysis, verdicts).

Floats are allowed here because nothing in this module feeds runtime
generation (ADR-002). OKLab (Ottosson 2020) is used for clustering and
nearest-colour search; relative luminance (WCAG) for hazard checks.
"""

from __future__ import annotations

import math


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    c = c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return max(0.0, min(255.0, c * 255.0))


def rgb_to_oklab(rgb) -> tuple[float, float, float]:
    r, g, b = (_lin(v) for v in rgb[:3])
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def oklab_to_rgb(lab) -> tuple[int, int, int]:
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(int(round(_gam(v))) for v in (r, g, bb))  # type: ignore[return-value]


def dist2(p, q) -> float:
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2


def rel_luminance(rgb) -> float:
    r, g, b = (_lin(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ramp(dark_rgb, light_rgb, n: int, hue_shift: float = 0.0) -> list[tuple[int, int, int]]:
    """n-step ramp between two colours in OKLab, optional hue shift
    (shadows toward cool, highlights toward warm — the pixel-art habit)."""
    a, b = rgb_to_oklab(dark_rgb), rgb_to_oklab(light_rgb)
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0
        L = a[0] + (b[0] - a[0]) * t
        A = a[1] + (b[1] - a[1]) * t
        B = a[2] + (b[2] - a[2]) * t
        if hue_shift:
            ang = hue_shift * (t - 0.5)
            A, B = A * math.cos(ang) - B * math.sin(ang), A * math.sin(ang) + B * math.cos(ang)
        out.append(oklab_to_rgb((L, A, B)))
    return out
