# Same seed, same sprite

**The contract:** the same type file (canonical hash) plus the same seed plus the same `ENGINE_MAJOR` gives identical pixels on every platform and in every language port.

## How it holds

1. **Canonical hash.** The type file is resolved, written as JSON with sorted keys and no spaces, then hashed with SHA-256. Comments and spacing cannot change it. A one-digit colour change always does.
2. **Master seed.** `SHA-256("PG" + type hash + seed as 8 bytes + ENGINE_MAJOR)`.
3. **Named streams.** Every decision reads from a named stream (`body`, `part/horns`, `shade`, `eyes`...). Each stream is `SHA-256(master + "/" + name)`. Adding a part adds a stream and leaves the others alone.
4. **Integer-only.** The runtime uses only whole numbers: xoshiro128** randomness, lowbias32 hashing, integer smoothstep noise, Bresenham lines. Floating point can differ between CPUs and compilers, so it is kept out.
5. **Tool-time floats.** Conversion (image to pixel art) uses OKLab colour maths. Its output is saved as pixels, so the runtime never repeats float work.

## How we know

- **B01** checks xoshiro128** against the published reference sequence, and runs one sprite in three processes with different hash seeds.
- **B03** compares 43 golden hashes.
- **B13** runs the JavaScript core under node and compares every golden, type hash and share code with Python.

## When it may change

Changing the pixels a type file and seed make is a breaking change. `tests/gate.py --bless-goldens` refuses to change a golden unless it gets `--witness` and `--reason`. A shipped change bumps `ENGINE_MAJOR`.

—Shibbieness
—Claude
