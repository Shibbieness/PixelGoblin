#!/usr/bin/env python3
"""PixelGoblin as an MCP server (stdio, standard library only).

It wraps the same engine as the command line, in the same process, so every
picture is byte-identical to what `python3 -m pixelgoblin ...` makes. Each tool
writes its files into an output folder and returns the path, a short summary,
and the picture itself when it is small enough to show inline.

Protocol: newline-delimited JSON-RPC 2.0 on stdin/stdout (MCP stdio transport).
Nothing but protocol messages is ever written to stdout; the engine's own
printing is captured.

    —Shibbieness
    —Claude
"""
from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = Path(os.environ.get("PIXELGOBLIN_ENGINE", HERE.parent / "skills" / "pixelgoblin" / "engine")).resolve()
sys.path.insert(0, str(ENGINE))

from pixelgoblin import CREDIT, VERSION, cli, typefile  # noqa: E402

PROTOCOL = "2025-06-18"
INLINE_LIMIT = 900_000  # bytes of PNG to return inline; bigger files are returned by path only


def out_dir() -> Path:
    d = Path(os.environ.get("PIXELGOBLIN_OUT") or (Path.home() / "PixelGoblin"))
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write-test"
        probe.write_text("ok")
        probe.unlink()
    except OSError:
        d = Path(tempfile.gettempdir()) / "PixelGoblin"
        d.mkdir(parents=True, exist_ok=True)
    return d


def slug(s: str) -> str:
    keep = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))
    return keep.strip("_")[:60] or "goblin"


def role_id(role: str) -> str:
    """Accept 'blacksmith', 'boc.goblin.blacksmith' or a file path."""
    if "." in role or "/" in role:
        return role
    return f"boc.goblin.{role}"


def mount_id(m: str) -> str:
    return m if "." in m else f"boc.mount.{m}"


def run_cli(argv: list[str]) -> tuple[int, str]:
    buf_out, buf_err = io.StringIO(), io.StringIO()
    rc = 0
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        try:
            rc = cli.main(argv)
        except SystemExit as e:  # argparse errors
            rc = e.code if isinstance(e.code, int) else 2
        except Exception:  # noqa: BLE001 - report, never crash the server
            rc = 1
            traceback.print_exc()
    text = (buf_out.getvalue() + buf_err.getvalue()).strip()
    return rc, text


def who(args: dict) -> list[str]:
    a = []
    if args.get("name"):
        a += ["--name", str(args["name"])]
    elif args.get("seed") is not None:
        a += ["--seed", str(int(args["seed"]))]
    return a


def looks(args: dict, era=True, team=True, sub=True, tier=True) -> list[str]:
    a = []
    if tier and args.get("tier"):
        a += ["--tier", str(int(args["tier"]))]
    if era and args.get("era"):
        a += ["--era", str(args["era"])]
    if team and args.get("clan"):
        a += ["--team", str(args["clan"])]
    if sub and args.get("sub"):
        a += ["--sub", str(args["sub"])]
    return a


def result(rc: int, text: str, files: list[Path]) -> dict:
    made = [f for f in files if f.exists()]
    content = [{"type": "text", "text": (text or "done") + ("\n\nFiles:\n" + "\n".join(str(f) for f in made) if made else "")}]
    for f in made:
        mime = {".png": "image/png", ".gif": "image/gif"}.get(f.suffix)
        if mime and f.stat().st_size <= INLINE_LIMIT:
            content.append({"type": "image", "data": base64.b64encode(f.read_bytes()).decode(), "mimeType": mime})
    return {"content": content, "isError": rc != 0}


# ---------------------------------------------------------------- tools

def t_list(args: dict) -> dict:
    kind = args.get("kind", "all")
    roles, mounts, cities, others = [], [], [], []
    for root in typefile.search_path():
        for p in typefile.type_files(root):
            try:
                tf = typefile.load(p)
            except typefile.TypeFileError:
                continue
            label = tf.data.get("label", "")
            if ".sub." in tf.id:
                others.append(f"{tf.id}  [overlay]")
                continue
            if tf.generator == "rig" and tf.data.get("role") and ".sub." not in tf.id:
                roles.append(f"{tf.id.split('.')[-1]}  ({label})")
            elif tf.generator == "beast":
                mounts.append(f"{tf.id.split('.')[-1]}  ({label})")
            else:
                others.append(f"{tf.id}  [{tf.generator}]")
    for root in typefile.search_path():
        for cp in sorted(Path(root).rglob("*.city.toml")):
            cities.append(cp.name.replace(".city.toml", ""))
    overlay_ids = sorted(o.split("  ")[0] for o in others if o.endswith("[overlay]"))
    others = [o for o in others if not o.endswith("[overlay]")]
    subs = [i.split(".")[-1] for i in overlay_ids if i.startswith("boc.goblin.sub.")]
    folk = [i.split(".")[-1] for i in overlay_ids if i.startswith("boc.race.sub.")]
    traits = [i.split(".")[-1] for i in overlay_ids if i.startswith("boc.trait.sub.")]
    packs = [f"{pk['id'].split('.')[-1]}  ({pk['label']}, {pk.get('counts', {}).get('types', 0)} types)" for pk in typefile.packs()]
    from pixelgoblin.gen import rig3d
    parts = {
        "jobs (roles)": sorted(roles),
        "clans": sorted(typefile.teams().keys()),
        "mounts": sorted(mounts),
        "variants (sub)": subs,
        "folk (sub, stackable)": folk,
        "traits (sub, stackable after a folk)": traits,
        "packs": packs,
        "cities": cities,
        "views": list(rig3d.VIEWS.keys()),
        "sizes (tier)": ["8", "16", "32", "64", "128", "256"],
        "colour eras": ["8-bit", "16-bit", "32-bit", "hd"],
        "other type files": sorted(others),
    }
    if kind != "all":
        parts = {k: v for k, v in parts.items() if k.startswith(kind)}
    text = f"PixelGoblin {VERSION}\n" + "\n".join(f"\n{k}:\n  " + "\n  ".join(v) for k, v in parts.items())
    return {"content": [{"type": "text", "text": text}], "isError": False}


def t_character(args: dict) -> dict:
    role = role_id(args.get("role", "blacksmith"))
    base = slug(args.get("name") or f"{role.split('.')[-1]}-{args.get('seed', 0)}")
    view = args.get("view")
    yaw, pitch = args.get("yaw"), args.get("pitch")
    anim = args.get("anim")
    ext = ".gif" if anim and not args.get("mount") else ".png"
    tag = view or (f"yaw{yaw}-pitch{pitch}" if yaw is not None or pitch is not None else "front")
    out = out_dir() / f"{base}-{role.split('.')[-1]}-{tag}{ext}"
    if args.get("mount"):
        argv = ["ride", role, mount_id(args["mount"]), "--out", str(out), "--scale", str(int(args.get("scale", 2)))]
        argv += ["--mount-seed", str(int(args.get("mount_seed", 0)))]
    else:
        argv = ["view", role, "--out", str(out), "--scale", str(int(args.get("scale", 2)))]
        if anim:
            argv += ["--anim", anim]
    argv += who(args) + looks(args)
    if view:
        argv += ["--view", view]
    if yaw is not None:
        argv += ["--yaw", str(int(yaw))]
    if pitch is not None:
        argv += ["--pitch", str(int(pitch))]
    if args.get("rim"):
        argv += ["--rim"]
    rc, text = run_cli(argv)
    return result(rc, text, [out])


SHEETS = {
    "card": "card",            # every size in the chain, labelled
    "turnaround": "turnaround",  # 8 directions
    "expressions": "expressions",
    "clans": "clans",
    "zoom": "zoom",            # GIF from crowd size to portrait
    "chain": "chain",          # folder: one PNG per size + chain.json
    "gif": "gif",              # idle or walk animation
}


def t_sheet(args: dict) -> dict:
    kind = args.get("kind", "card")
    if kind not in SHEETS:
        return {"content": [{"type": "text", "text": f"Unknown sheet kind {kind!r}. Use one of: {', '.join(SHEETS)}."}], "isError": True}
    role = role_id(args.get("role", "blacksmith"))
    base = slug(args.get("name") or f"{role.split('.')[-1]}-{args.get('seed', 0)}")
    d = out_dir()
    if kind == "chain":
        out = d / f"{base}-{role.split('.')[-1]}-chain"
    else:
        out = d / f"{base}-{role.split('.')[-1]}-{kind}{'.gif' if kind in ('zoom', 'gif') else '.png'}"
    argv = [SHEETS[kind], role, "--out", str(out)] + who(args)
    if kind in ("card", "turnaround", "expressions", "clans", "gif", "zoom"):
        argv += ["--scale", str(int(args.get("scale", 2 if kind != "card" else 1)))]
    if kind in ("card", "turnaround", "expressions", "clans", "chain", "gif", "zoom"):
        argv += looks(args, team=kind != "clans", tier=kind != "chain")
    if kind == "turnaround" and args.get("pitch") is not None:
        argv += ["--pitch", str(int(args["pitch"]))]
    if kind == "gif" and args.get("anim"):
        argv += ["--anim", args["anim"]]
    rc, text = run_cli(argv)
    files = sorted(out.glob("*.png")) if out.is_dir() else [out]
    return result(rc, text, files)


def t_city(args: dict) -> dict:
    city = args.get("city", "boc.city.goblintown")
    if "." not in city:
        city = f"boc.city.{city}"
    d = out_dir() / slug(args.get("folder") or city.split(".")[-1])
    d.mkdir(parents=True, exist_ok=True)
    names = args.get("names")
    if names:
        nf = d / "names.txt"
        nf.write_text(names if isinstance(names, str) else "\n".join(names))
    else:
        nf = ENGINE / "flavors" / "boc" / "village" / "goblintown.names.txt"
    argv = ["city", city, str(nf), "--out", str(d), "--seed", str(int(args.get("seed", 1))), "--tier", str(int(args.get("tier", 64)))]
    rc, text = run_cli(argv)
    summary = ""
    cj = d / "census.json"
    if cj.exists():
        people = json.loads(cj.read_text())["citizens"]
        rows = [f"{p['name']}: {p['role'].split('.')[-1].replace('_', ' ')}, household {p['household']}" + (f", clan {p['team']}" if p.get("team") else "") for p in people]
        summary = "\n\nCensus:\n" + "\n".join(rows)
    return result(rc, text + summary, [d / "village.png", d / "citizens.png"])


def t_cli(args: dict) -> dict:
    argv = [str(x) for x in args.get("args", [])]
    if not argv:
        return {"content": [{"type": "text", "text": "Give the command as a list, for example [\"list\"] or [\"view\", \"boc.goblin.scout\", \"--name\", \"Mizzle\", \"--view\", \"iso_sw\", \"--out\", \"scout.png\"]."}], "isError": True}
    # relative --out paths go into the output folder, not wherever the server happens to run
    for i, v in enumerate(argv[:-1]):
        if v == "--out" and not os.path.isabs(argv[i + 1]):
            argv[i + 1] = str(out_dir() / argv[i + 1])
    rc, text = run_cli(argv)
    files = []
    if "--out" in argv:
        o = Path(argv[argv.index("--out") + 1])
        files = sorted(o.glob("*.png"))[:6] if o.is_dir() else [o]
    return result(rc, text, files)


def t_pack(args: dict) -> dict:
    name = str(args.get("pack", "races"))
    out = out_dir() / f"pack-{slug(name)}.png"
    argv = ["pack", name, "--out", str(out), "--scale", str(int(args.get("scale", 2)))]
    if args.get("role"):
        argv += ["--role", role_id(args["role"])]
    if args.get("seed") is not None:
        argv += ["--seed", str(int(args["seed"]))]
    rc, text = run_cli(argv)
    if rc != 0 and "data only" in text:
        rc2, listing = run_cli(["packs"])
        text += "\n\n" + listing
    return result(rc, text, [out] + sorted(out.parent.glob(f"{out.stem}-*.png")))


def t_avatar(args: dict) -> dict:
    soul = str(args.get("soul", "Aelren"))
    out = out_dir() / f"avatar-{slug(soul)}-{args.get('view', 'front')}.png"
    argv = ["avatar", soul, "--out", str(out), "--scale", str(int(args.get("scale", 3))), "--view", str(args.get("view", "front"))]
    if args.get("role"):
        argv += ["--role", role_id(args["role"])]
    if args.get("sub"):
        argv += ["--sub", str(args["sub"])]
    if args.get("tier"):
        argv += ["--tier", str(int(args["tier"]))]
    rc, text = run_cli(argv)
    side = out.with_suffix(".json")
    if side.exists():
        text += "\n\n" + side.read_text()
    return result(rc, text, [out])


def t_sandbox(args: dict) -> dict:
    biome = str(args.get("biome", "forest"))
    seed = int(args.get("seed", 1))
    d = out_dir() / f"grounds-{slug(biome)}-{seed}"
    rc, text = run_cli(["sandbox", "--biome", biome, "--seed", str(seed), "--size", str(args.get("size", "28x18")), "--out", str(d)])
    return result(rc, text + "\n\nPlay it: open skills/pixelgoblin/pages/pixelgoblin-grounds.html, pick the same biome and seed.", [d / "map.png"])


def t_selftest(args: dict) -> dict:
    """Quick health check: validate every type file and draw one goblin two ways."""
    rc, text = run_cli(["validate"] + [str(p) for p in typefile.search_path()])
    out = out_dir() / "selftest-grubnak.png"
    rc2, text2 = run_cli(["view", "boc.goblin.blacksmith", "--name", "Grubnak", "--view", "iso_sw", "--out", str(out)])
    ok = rc == 0 and rc2 == 0 and out.exists()
    msg = f"{'OK' if ok else 'PROBLEM'}: engine at {ENGINE}\noutput folder {out_dir()}\n\nvalidate:\n{text}\n\nview:\n{text2}"
    return result(0 if ok else 1, msg, [out])


STR = {"type": "string"}
INT = {"type": "integer"}
WHO = {
    "role": {"type": "string", "description": "The job, like blacksmith, shaman, scout, guard, miner, fisher, rider (see pixelgoblin_list). A full id like boc.goblin.shaman also works."},
    "name": {"type": "string", "description": "A name. The same name always makes the same goblin. Use this or seed."},
    "seed": {"type": "integer", "description": "A whole number instead of a name."},
    "clan": {"type": "string", "description": "Clan colours: ashfang, cinderglass, duskveil, gildhand, mossback, skyrope, tidecaller."},
    "sub": {"type": "string", "description": "Overlays, comma-separated, applied left to right: a goblin variant (snow, cave), a folk from the races pack (dwarf, elf, orc, halfling, merfolk...) and/or a Compendium trait (axis_frost, axis_flame...)."},
    "tier": {"type": "integer", "enum": [8, 16, 32, 64, 128, 256], "description": "Size in pixels."},
    "era": {"type": "string", "enum": ["8-bit", "16-bit", "32-bit", "hd"], "description": "Colour era. Leave out to use the size's own era."},
    "scale": {"type": "integer", "description": "Upscale the saved file (pixels stay square). Default 2."},
}

TOOLS = [
    ({"name": "pixelgoblin_list", "title": "List what PixelGoblin can make",
      "description": "List the jobs, clans, mounts, variants, cities, views, sizes and colour eras PixelGoblin knows. Call this first when unsure of a name.",
      "inputSchema": {"type": "object", "properties": {"kind": {"type": "string", "description": "Optional filter: jobs, clans, mounts, variants, folk, traits, packs, cities, views, sizes, colour, other."}}},
      "annotations": {"readOnlyHint": True}}, t_list),
    ({"name": "pixelgoblin_character", "title": "Draw one goblin",
      "description": "Draw one goblin character from any direction: front, side, back, isometric, top-down, or any turn and tilt. Optionally riding a mount, or as a walking/idle GIF. Returns the picture and its file path.",
      "inputSchema": {"type": "object", "properties": dict(WHO, **{
          "view": {"type": "string", "enum": ["front", "back", "side_left", "side_right", "iso_sw", "iso_se", "iso_nw", "iso_ne", "top", "three_quarter"]},
          "yaw": {"type": "integer", "description": "Free turn in degrees: 0 front, 90 facing left, 180 back, 270 facing right."},
          "pitch": {"type": "integer", "description": "Tilt in degrees: 0 level, 30 isometric, 90 straight down."},
          "mount": {"type": "string", "description": "Ride a mount: boar or wolf."},
          "mount_seed": INT,
          "anim": {"type": "string", "enum": ["idle", "walk_side"], "description": "Write a GIF of this motion instead of a still (not with a mount)."},
          "rim": {"type": "boolean", "description": "Light rim outline, for dark backgrounds."}}), "required": ["role"]}}, t_character),
    ({"name": "pixelgoblin_sheet", "title": "Make a goblin sheet",
      "description": "Make a sheet for one goblin: card (every size from 8 to 256 px), turnaround (8 directions), expressions (9 faces), clans (the goblin in every clan's colours), zoom (GIF from crowd size to portrait), chain (one PNG per size plus chain.json for game engines), or gif (idle or walk animation).",
      "inputSchema": {"type": "object", "properties": dict(WHO, **{
          "kind": {"type": "string", "enum": list(SHEETS)},
          "pitch": {"type": "integer", "description": "Tilt for the turnaround (default 0; 30 for isometric)."},
          "anim": {"type": "string", "enum": ["idle", "walk"], "description": "For kind gif."}}), "required": ["kind", "role"]}}, t_sheet),
    ({"name": "pixelgoblin_city", "title": "Build a city from names",
      "description": "Build a whole goblin population from a list of names: each name becomes a citizen with a job, household, clan and look (children resemble their parents), then the village with them in it. Returns village.png, citizens.png and census.json.",
      "inputSchema": {"type": "object", "properties": {
          "names": {"description": "One citizen per line (text), or a list of names. Leave out to use Goblintown's 35 citizens. A surname that matches a clan joins that clan.",
                    "anyOf": [STR, {"type": "array", "items": STR}]},
          "city": {"type": "string", "description": "City file id, default boc.city.goblintown."},
          "seed": INT, "tier": {"type": "integer", "enum": [16, 32, 64, 128]},
          "folder": {"type": "string", "description": "Name of the output sub-folder."}}}}, t_city),
    ({"name": "pixelgoblin_pack", "title": "Show a resource pack",
      "description": "Show every sprite in one resource pack on one sheet: races (Folk of the Book of Cities), biomes, flora (plants and fungi), fauna (animals and fish), ores (grounded in CRUCIBLE), compendium (ranks and trait overlays). Races and traits are drawn on a job. aether and world hold data only.",
      "inputSchema": {"type": "object", "properties": {"pack": {"type": "string", "enum": ["races", "biomes", "flora", "fauna", "ores", "compendium", "aether", "world"]},
                                                        "role": {"type": "string", "description": "Job that shows races and traits (default guard)."}, "seed": INT,
                                                        "scale": INT}, "required": ["pack"]}}, t_pack),
    ({"name": "pixelgoblin_avatar", "title": "Draw an Aether Library soul",
      "description": "Draw an avatar for a named soul (Aether Library souls such as Aelren, Hessel, Tiwa, or any name). Seeded from the soul name, so it survives reincarnation. Offered as a supplement: it never replaces an existing identity.",
      "inputSchema": {"type": "object", "properties": {"soul": STR, "role": STR, "sub": {"type": "string", "description": "Folk or trait overlays, comma-separated (dwarf, elf,axis_frost)."},
                                                        "view": {"type": "string", "enum": ["front", "back", "side_left", "side_right", "iso_sw", "iso_se", "iso_nw", "iso_ne", "top", "three_quarter"]},
                                                        "tier": {"type": "integer", "enum": [8, 16, 32, 64, 128, 256]}, "scale": INT}, "required": ["soul"]}}, t_avatar),
    ({"name": "pixelgoblin_sandbox", "title": "Build a Goblin Grounds world",
      "description": "Build a Goblin Grounds sandbox world from a Book of Cities biome: ground, water, rock, plants, fungi and ores to gather (weights from CRUCIBLE), animals, a forge and quests. Returns map.png and writes world.json + atlas.png for game engines. The same biome and seed make the same world in the Goblin Grounds page.",
      "inputSchema": {"type": "object", "properties": {"biome": {"type": "string", "enum": ["forest", "mountain", "coast", "swamp", "plain", "desert", "tundra", "badlands", "underwater"]},
                                                        "seed": INT, "size": {"type": "string", "description": "Tiles, like 28x18 (12x10 to 64x48)."}}}}, t_sandbox),
    ({"name": "pixelgoblin_cli", "title": "Run any PixelGoblin command",
      "description": "Run any of PixelGoblin's 32 commands directly, for anything the other tools don't cover (convert an image, autotile, wfc, uikit, validate, verdict, squint, likeness, ascii, brood, roster, anim, sheet, gen, share, watch). Give the arguments as a list, exactly as on the command line after 'pixelgoblin'. Relative --out paths go into the output folder.",
      "inputSchema": {"type": "object", "properties": {"args": {"type": "array", "items": STR}}, "required": ["args"]}}, t_cli),
    ({"name": "pixelgoblin_selftest", "title": "Check PixelGoblin works",
      "description": "Check that the engine is installed and working: validates every type file and draws Grubnak. Also reports where pictures are saved.",
      "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": False}}, t_selftest),
]
HANDLERS = {spec["name"]: fn for spec, fn in TOOLS}


def handle(msg: dict):
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        want = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": want,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "pixelgoblin", "title": "PixelGoblin", "version": VERSION},
            "instructions": f"PixelGoblin {VERSION}: deterministic pixel-art goblins. Same name, same goblin. Pictures are saved to {out_dir()}. {CREDIT}"}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": [spec for spec, _ in TOOLS]}}
    if method == "tools/call":
        p = msg.get("params") or {}
        fn = HANDLERS.get(p.get("name"))
        if not fn:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {p.get('name')}"}}
        try:
            return {"jsonrpc": "2.0", "id": mid, "result": fn(p.get("arguments") or {})}
        except Exception as e:  # noqa: BLE001
            return {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": f"error: {e}"}], "isError": True}}
    if mid is None:  # a notification, like notifications/initialized
        return None
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
