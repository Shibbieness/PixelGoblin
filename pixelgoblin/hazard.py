"""The hazard layer — the part where being wrong hurts someone.

Two hazards, each stated as mechanism first (SPIRE's rule: a bare "don't"
gets worked around; a "because" generalises):

1. PHOTOSENSITIVE FLASHING. Animated sprites, UI and backgrounds can flash.
   Flashing between light and dark more than three times a second, over a
   large enough area, can trigger seizures in people with photosensitive
   epilepsy — and it can happen to someone who has never had one before.
   The check here approximates the WCAG 2.x general-flash rule (three
   flashes in any one second; a flash is a pair of opposing relative-
   luminance changes of 10% or more where the darker state is below 0.80).
   It measures area as a fraction of the frame, because a sprite's real
   on-screen size is unknown at export. It is an APPROXIMATION, not a
   certified test (tools like PEAT exist for that) — status UNVERIFIED.

2. LICENCE CONTAMINATION. A non-commercial or share-alike input inside a
   commercial bundle exposes whoever ships it. Blocking is a bundle-profile
   judgement; detection only reports.

Detection never silently decides: every finding is returned with its
mechanism, and findings are written into export provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .color import rel_luminance

FLASH_MECHANISM = (
    "Do not ship this animation as-is. Here is what happens: it flashes between light and dark "
    "{count} times within one second over {area}% of the frame. Here is why that matters: rapid "
    "light/dark flashing can trigger seizures in people with photosensitive epilepsy, including "
    "people who have never had one. Here is what to do instead: slow it to 3 flashes per second or "
    "fewer (longer frame_ms), reduce the brightness difference, or shrink the flashing area."
)

NC_MARKERS = ("NC", "NonCommercial", "Noncommercial")


@dataclass
class Finding:
    kind: str
    severity: str
    mechanism: str
    detail: dict = field(default_factory=dict)
    status: str = "UNVERIFIED"


def flash_check(frames, frame_ms: int, area_threshold_pct: int = 25, max_per_sec: int = 3, loop: bool = True) -> list[Finding]:
    if len(frames) < 2:
        return []
    lum = [[rel_luminance(f.palette[i]) if i else None for i in f.px] for f in frames]
    seq = list(range(len(frames)))
    reps = max(1, (1000 // max(1, frame_ms)) + 2) if loop else 1
    order = (seq * (reps * 2))[: max(len(seq), (2000 // max(1, frame_ms)) + 2)] if loop else seq
    n = len(frames[0].px)
    transitions = []  # (time_ms, direction) for each frame change with a big-area luminance swing
    for t in range(1, len(order)):
        a, b = lum[order[t - 1]], lum[order[t]]
        up = down = 0
        for i in range(n):
            if a[i] is None or b[i] is None:
                continue
            if abs(a[i] - b[i]) >= 0.1 and min(a[i], b[i]) < 0.8:
                if b[i] > a[i]:
                    up += 1
                else:
                    down += 1
        area = max(up, down) * 100 // max(1, n)
        if area >= area_threshold_pct:
            transitions.append((t * frame_ms, 1 if up >= down else -1, area))
    worst, worst_area = 0, 0
    for i in range(len(transitions)):
        window = [tr for tr in transitions if transitions[i][0] <= tr[0] < transitions[i][0] + 1000]
        flips = sum(1 for j in range(1, len(window)) if window[j][1] != window[j - 1][1])
        flashes = (flips + 1) // 2 if window else 0
        if flashes > worst:
            worst, worst_area = flashes, max(tr[2] for tr in window)
    if worst > max_per_sec:
        return [Finding("photosensitive-flash", "high", FLASH_MECHANISM.format(count=worst, area=worst_area),
                        {"flashes_per_second": worst, "area_pct": worst_area, "frame_ms": frame_ms})]
    return []


def licence_check(licences: list[str], profile: str) -> list[Finding]:
    """profile: 'commercial' | 'open'."""
    import re
    out = []
    for lic in licences:
        tokens = set(re.split(r"[-_ .]", lic))
        nc = "NC" in tokens or any(m in lic for m in NC_MARKERS[1:])
        sa = "SA" in tokens or "ShareAlike" in lic or lic.startswith(("GPL", "AGPL", "LGPL"))
        if profile == "commercial" and nc:
            out.append(Finding("licence-noncommercial", "high",
                               f"Do not bundle '{lic}' into a commercial pack. Here is what happens: a non-commercial "
                               f"licence forbids selling it, so everyone who buys the pack is exposed. Here is what to do "
                               f"instead: replace it, get written permission, or ship an open (non-commercial) pack.",
                               {"licence": lic}, "VERIFIED"))
        elif profile == "commercial" and sa:
            out.append(Finding("licence-sharealike", "medium",
                               f"'{lic}' is share-alike. Here is what happens: a closed commercial pack that includes it "
                               f"must be released under the same terms, or it breaks the licence. Here is what to do "
                               f"instead: keep it in the open pack, or relicense it if you hold the rights.",
                               {"licence": lic}, "VERIFIED"))
    return out
