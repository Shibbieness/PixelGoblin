"""PixelGoblin — deterministic pixel art generator, converter and runtime.

Built on PixelGoblin — © Shibbieness / M MAOU LLC

The engine contract: same type file (canonical hash) + same seed + same
ENGINE_MAJOR produces identical pixels on every platform and in every
language port. Runtime generation is integer-only; floats appear only in
tool-time conversion (image -> pixel art), whose output is saved as pixels.
"""

VERSION = "v0u1p0"          # VUP: v = architectural, u = consolidation, p = patch
ENGINE_MAJOR = 0            # bump = pixel-output contract changes; goldens regenerate
CREDIT = "Built on PixelGoblin — © Shibbieness / M MAOU LLC"

__all__ = ["VERSION", "ENGINE_MAJOR", "CREDIT"]
