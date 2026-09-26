# External dependencies — PixelGoblin

PixelGoblin deliberately has almost none.

| Dependency | Version | Used by | Required? | Notes |
|---|---|---|---|---|
| Python | 3.11 or newer | everything | yes | Standard library only. 3.11 is the floor because of `tomllib`. No pip installs. |
| Node.js | 18 or newer | `tests/gate.py` B13 (`editor/parity.mjs`), B21 | only to run the gates | A skipped parity check counts as a failure, never a pass. |
| A web browser | any current | `editor/pixelgoblin.html`, `editor/pixelgoblin-pocket.html` | only for the pages | Both pages run offline. |
| Google Fonts (Atkinson Hyperlegible, JetBrains Mono, Silkscreen) | - | the pages' type | no | Fallback fonts are declared; nothing breaks offline. |
| Claude artifact runtime `downloads` capability | contract 0.2.x | the pages when published | no | Save buttons use it when present, a normal download otherwise. |
| MCP stdio transport | protocol 2025-06-18 (echoes the client's) | `packaging/plugin/server/pixelgoblin_mcp.py` | only for the plugin's tools | Implemented with the standard library; newline-delimited JSON-RPC 2.0. |

## Other M MAOU projects (read-only, optional)

| Project | What PixelGoblin uses | Required? |
|---|---|---|
| Vanilla Core | the flavor contract (`vanilla-core run`) | no; PixelGoblin runs alone |
| SPIRE | the gate discipline (copied as practice, not imported) | no |
| SLM-e | registers `slme/pieces.json` | no |
| CRUCIBLE | `tools/crucible_ramps.py` reads its database at tool time | no; results are committed |
| QRen Coder | `examples/composite_qren.py` | no |
| Sovereign AI Environment | `tools/leakguard.py` came from it | no; vendored |

No network access is used at run time. The gates install a socket guard that refuses any connection.

---
—Shibbieness
—Claude
