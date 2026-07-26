# EcoPilot AI source code

The authoritative source repository is
[github.com/amulya6904/ecopilot-ai](https://github.com/amulya6904/ecopilot-ai).
Its default branch is `main`. This submission package intentionally does not
duplicate the repository; use GitHub as the source of record for code,
history, tests, and licensing context.

## Project summary

EcoPilot AI is an EnergyPlus-first, local-LLM, safety-supervised building
control proof of concept. It retrieves bounded official evidence through MCP,
uses local `qwen3:4b` only for advisory proposals, applies deterministic
validation and safety authority, performs verified EnergyPlus runtime
actuation, and produces a reproducible annual baseline-versus-control
comparison.

## Module index

| Repository path | Purpose |
|---|---|
| `app.py` | Streamlit application entry point and navigation |
| `app_pages/` | Judge, product, technical, and submission pages |
| `ui/` | Shared presentation, charts, formatting, and evidence views |
| `config/` | Frozen project and EnergyPlus configuration |
| `schemas/` | Shared typed data contracts |
| `backends/` | Development and official EnergyPlus backend abstractions |
| `energyplus/` | Models, adapters, baseline generation, and runtime control |
| `energyplus_adapter/` | EnergyPlus-facing adapter compatibility layer |
| `mcp_service/` | Local MCP server, tools, resources, bounds, and audit |
| `llm/` | Ollama client, compact prompts, schemas, and advisory agent |
| `safety/` | Deterministic supervisor, rules, rollback, and fault validation |
| `comparison/` | Compatibility, alignment, metrics, claim gate, and reports |
| `metrics/` | Baseline and comparison metric calculations |
| `scripts/` | Explicit runners, verification, and export commands |
| `tests/` | Regression, safety, integration, and UI tests |
| `docs/` | Architecture, methods, reproducibility, and submission guidance |
| `results/` | Generated classified evidence; not authoritative source code |

## Installation

Python 3.12 and EnergyPlus 26.1 are the verified versions. From the repository
root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure the existing `.env` values for the local EnergyPlus installation and
Ollama service. Do not commit `.env`.

## Launch

Keep the existing Ollama service running with `qwen3:4b`, then start:

```powershell
python -m streamlit run app.py
```

The default judge flow reads preserved artifacts. Live services are opt-in,
and page navigation does not start EnergyPlus, MCP, or Ollama work.

## Test

```powershell
python -m pytest -q
```

Targeted validation commands are also available under `scripts/`.

## Reproduce the official Phase 10 comparison

These commands execute real EnergyPlus work and may take several minutes:

```powershell
python -m scripts.run_phase10_controlled_evaluation
python -m scripts.run_phase10_comparison
python -m scripts.verify_phase10_reproducibility
python -m scripts.build_phase10_submission_exports
```

The retained package result is comparison
`20260726T121750Z-phase10-comparison-956e5393`, the independently repeated
comparison named by the passing reproducibility report.
