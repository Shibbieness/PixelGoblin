# pretune/ — PixelGoblin Workshop

Tags: #test #complete #validated

The place for trying variations before anything is trusted. PixelGoblin is deterministic, so pretuning asks one thing: **does the engine still make exactly these pictures?**

## What is here

| Folder | What it holds |
|---|---|
| `scenarios/` | Twelve scenarios as JSON: the request, the exact command, and the SHA-256 of every file it must make. |
| `expected_outputs/` | The files themselves, made at forge. Open them to see the goblins, folk, packs and worlds. |
| `results/` | One results file per run. |

## How to run them

Unpack the source, then run each scenario from the unpacked folder (the capsule root is `CAP` below):

```bash
python3 CAP/build/source/workshop.py unpack /tmp/pg
cd /tmp/pg
for f in CAP/pretune/scenarios/*.json; do
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

Copy a scenario, change one thing (a name, a view, an era), run it, and look. A scenario that should stay goes to `updates/tests/` through Companion Builder mode, and, if it guards a behaviour, becomes a gate check in the source.

—Shibbieness
—Claude
