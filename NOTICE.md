# Notice

PixelGoblin
Copyright (c) 2026 Shibbieness (Mark) · M MAOU LLC

## Authorship and affiliation

Authored by Shibbieness with AI assistance (Claude). PixelGoblin is an
independent project and is not affiliated with or endorsed by Anthropic or
any AI vendor — the tooling is incidental, the way a compiler or an IDE is.

Practical consequence: commits, files, and docs here carry the maintainer's
name, not a vendor's. No vendor email addresses in author fields, no vendor
co-author trailers, no links back to private chat sessions. `tools/leakguard.py`
enforces this by machinery, not by memory.

## License

PixelGoblin is licensed under AGPL-3.0-or-later (`LICENSE`): free to use,
modify, and redistribute, on the condition that modified versions and
network services built on it stay open under the same terms. A commercial
license waiving that condition is intended to be available — see
`LICENSE-COMMERCIAL.md`.

A small attribution requirement applies under AGPL-3.0 §7(b); see
`ATTRIBUTION.md`.

## What the license covers, and what it does not

- **The engine** (code in `pixelgoblin/`, `editor/`, `tools/`, `tests/`) is
  AGPL-3.0-or-later.
- **Sprites you generate or convert are yours.** Output of a program is not
  covered by the program's license. Every type file declares its own
  `license` field, and that license travels with the sprites made from it
  (it is written into every export's provenance record).
- **Type files in `types/vanilla/`** are AGPL-3.0-or-later like the engine.
  Mark may relicense them (for example CC0) at any time as sole copyright
  holder; that is a separate decision and has not been made here.
- **`flavors/boc/`** is Book of Cities flavor content: it is excluded from the
  vanilla build and is not part of what a third party receives by default.

## License text provenance

`LICENSE` is the GNU Affero General Public License v3.0, copied byte-for-byte
from the QRen-Code-Build-1 repository, whose `NOTICE.md` records its origin
(the `matrix-synapse` source distribution on PyPI). SHA-256
`0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0`, checked by
build gate B00 on every run.

Verify before relying on it:

```
curl -sS https://www.gnu.org/licenses/agpl-3.0.txt | diff - LICENSE
```

If a discrepancy is found, the gnu.org text controls.

## Not legal advice

Nothing here has been reviewed by an attorney. It reflects the maintainer's
plain-language intent: free for individuals, students, nonprofits, and small
commercial use; anything built on top stays free; a paid commercial license
is available for anyone who wants out of that obligation.

—Shibbieness
—Claude
