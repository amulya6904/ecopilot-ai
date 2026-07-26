# Source manifest

GitHub is the authoritative source deliverable:
`https://github.com/amulya6904/ecopilot-ai`, default branch `main`.

| Source path | Purpose | Included in this ZIP |
|---|---|---|
| `app.py`, `app_pages/`, `ui/`, `assets/` | Streamlit product and technical interface | No; reference GitHub |
| `config/`, `schemas/`, `storage/` | Configuration, contracts, and persistence helpers | No; reference GitHub |
| `backends/`, `simulator/` | Backend abstraction and development-only simulator | No; reference GitHub |
| `energyplus/`, `energyplus_adapter/` | Official EnergyPlus model, baseline, telemetry, and runtime integration | Building artifacts only |
| `mcp_service/` | Bounded local evidence service and audit layer | No; reference GitHub |
| `llm/` | Local Ollama advisory agent and structured proposal path | No; reference GitHub |
| `safety/`, `controllers/` | Deterministic control authority, guardrails, and fallback | No; reference GitHub |
| `comparison/`, `metrics/`, `prediction/`, `explanations/` | Validated metrics, comparison, and explanations | Quantitative artifacts only |
| `scripts/` | Explicit run, validation, reproducibility, and export commands | No; reference GitHub |
| `tests/` | Automated regression and acceptance suite | No; reference GitHub |
| `docs/` | Project and architecture documentation | Architecture deliverable only |

Excluded by design: `.env`, virtual environments, caches, compiled files,
credentials, local logs, raw EnergyPlus outputs, and unrelated generated
artifacts.
