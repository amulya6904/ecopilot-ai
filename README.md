# EcoPilot AI

**Autonomous Smart Building Energy and Comfort Optimization**

EcoPilot AI is a two-day Honeywell recruitment hackathon project. It addresses the
problem of balancing occupant comfort, indoor air quality, energy cost, and carbon
impact in commercial buildings. The proposed solution is a future deterministic,
predictive, closed-loop controller with an independent safety supervisor and a fixed
baseline for fair comparison.

## Phase 1 status

Phase 1 freezes requirements, configures three zones and system constraints, creates
the development structure, and provides a Streamlit configuration dashboard and
tests. It contains no simulation, optimization, autonomous control, or claimed
energy savings.

## Future architecture

Future sensor/state inputs will feed a custom multi-zone simulator and forecasts.
A deterministic optimizer will evaluate candidate HVAC actions, a safety supervisor
will accept or reject them, and closed-loop execution will update the simulator.
The dashboard will compare the result with a non-intelligent fixed-schedule baseline.
MCP and a local LLM will later provide tool-based natural-language interaction;
EnergyPlus will remain behind an adapter.

## Building zones

| ID | Zone | Area | Capacity | Heat level | HVAC limit |
|---|---|---:|---:|---|---:|
| `office` | Open Office | 150 m² | 30 | Medium | 12 kW |
| `conference` | Conference Room | 50 m² | 12 | Low | 6 kW |
| `lab` | Computer Lab | 100 m² | 25 | High | 14 kW |

## Configuration summary

- Simulation: 08:00–20:00, 5-minute intervals, 144 total steps
- Forecast horizon: 3 steps (15 minutes)
- Occupied preferred range: 23–24°C; allowed range: 22–25°C
- HVAC candidates: setpoints 21–27°C, fan speeds 30/50/70/90%, and
  low/medium/high ventilation
- Baseline: fixed occupied and unoccupied schedules; it does not respond to actual
  occupancy
- Future objective: energy cost + comfort penalty + CO2 penalty + carbon penalty +
  control-change penalty

## Repository structure

`config/` contains the only operational domain code in Phase 1. `app.py` renders the
configuration shell, and `tests/` validates it. The remaining packages reserve clear
boundaries for the simulator, controllers, prediction, explanations, persistence,
expanded UI, MCP, LLM, and EnergyPlus adapter; their modules are documentation-only.

## Installation (Windows PowerShell)

Python 3.11 or newer is required.

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

EnergyPlus, MCP, and Ollama are intentionally not installed during Phase 1.

## Run and test

```powershell
pytest -q
streamlit run app.py
```

The expected Phase 1 dashboard shows the three zones, timing and comfort KPIs,
safety constraints, fixed baseline configuration, future optimizer candidates, and
the phase roadmap. It shows no live sensor readings or performance claims.

## Current limitations and next phase

There is no building/weather/occupancy/CO2/energy simulation, controller, predictor,
safety execution, database, MCP service, LLM integration, EnergyPlus integration, or
real-time charting. Phase 2 will implement the custom building simulator only.

## Troubleshooting

- If activation is blocked, run the provided process-scoped `Set-ExecutionPolicy`
  command and activate again.
- If `streamlit` or `pytest` is not recognized, activate the virtual environment and
  run `pip install -r requirements.txt`.
- Run commands from the repository root so Python can import `config`.
- If port 8501 is occupied, use `streamlit run app.py --server.port 8502`.
