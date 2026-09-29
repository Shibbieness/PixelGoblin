import sys

from .cli import main

for _s in (sys.stdout, sys.stderr):  # a pipe on Windows defaults to cp1252; write UTF-8 everywhere
    _s.reconfigure(encoding="utf-8")
sys.exit(main())
