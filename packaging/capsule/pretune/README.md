# pretune/ — PixelGoblin

Tags: #test #complete #validated

The sandbox for trying variations before anything is trusted. Because PixelGoblin is deterministic, pretuning here means one thing: **does the engine still make exactly these goblins?**

## What is here

| Folder | What it holds |
|---|---|
| `scenarios/` | Eight scenarios as JSON: what the request was, the exact command, and the SHA-256 of every file it must produce. |
| `expected_outputs/` | The files themselves, made at forge. Open them to see the goblins. |
| `results/` | One results file per run. The forge run is `forge-20260926.md`. |

The scenarios cover the main ways Mark asks for goblins: a named goblin in isometric, a clan-coloured side view, an 8-direction turnaround, a rider on a warg from behind, a snow miner in 8-bit, a character card, an expression sheet, and Goblintown from its names.

## How to run them

From the capsule root (or a copy of `build/source/`):

```bash
cd build/source
for f in ../../pretune/scenarios/*.json; do
  python3 - "$f" <<'EOF'
import json, sys, subprocess, hashlib, pathlib, tempfile
s = json.load(open(sys.argv[1]))
out = pathlib.Path(tempfile.mkdtemp())
cmd = [sys.executable] + s["command"][1:]
i = cmd.index("--out"); cmd[i + 1] = str(out / cmd[i + 1])
subprocess.run(cmd, check=True, capture_output=True, env={"PYTHONHASHSEED": "0", "PATH": "/usr/bin:/bin"})
bad = [k for k, h in s["expected_sha256"].items() if hashlib.sha256((out / k).read_bytes()).hexdigest() != h]
print(s["id"], "PASS" if not bad else f"FAIL {bad}")
EOF
done
```

## How to use it for variations

Copy a scenario, change one thing (a name, a view, an era), run it, and look. A new scenario that should become permanent goes to `updates/tests/` through Companion Builder mode, and, if it guards a behaviour, becomes a gate check in the repository.

## What this is not

Not the gates. The gates (`build/source/tests/gate.py`) prove the engine's contracts; pretune shows specific pictures still come out the same.

---
—Shibbieness
—Claude
