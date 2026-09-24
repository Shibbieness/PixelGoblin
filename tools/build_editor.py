#!/usr/bin/env python3
"""Build editor/pixelgoblin.html from editor/src.html.

Embeds the exact text of editor/pg-core.js (gate B13 checks it) and every
type file on the search path, resolved by the Python engine, so the page
runs fully offline as one file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pixelgoblin import CREDIT, VERSION, typefile  # noqa: E402


def main() -> int:
    types = []
    for root in typefile.search_path():
        for p in sorted(root.rglob("*.toml")):
            if p.name == "tags.toml":
                continue
            tf = typefile.load(p)
            types.append({"data": tf.data, "flavor": not tf.id.startswith("vanilla."), "hash": tf.type_hash})
    tax = typefile.taxonomy()
    tags = [{"name": name, "profile": typefile.profile_for(name)} for name in tax.get("tag", {})]
    presets = {"version": VERSION, "credit": CREDIT, "types": types, "tags": tags}
    src = (ROOT / "editor" / "src.html").read_text()
    core = (ROOT / "editor" / "pg-core.js").read_text()
    html = src.replace("/*__PG_CORE__*/", core).replace("/*__PRESETS__*/", json.dumps(presets, ensure_ascii=False))
    (ROOT / "editor" / "pixelgoblin.html").write_text(html)
    print(f"editor/pixelgoblin.html  {len(html) // 1024} KB  {len(types)} types  {len(tags)} tag profiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
