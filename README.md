# EcoPilot AI

**Autonomous Smart Building Energy and Comfort Optimization**

EcoPilot AI is a Honeywell recruitment hackathon project exploring transparent,
safe HVAC control for a three-zone commercial building. Phase 1 froze requirements
and configuration. **Phase 2 — Custom Multi-Zone Building Simulator is complete.**
Prediction, controllers, optimization, and autonomous operation are not implemented.

> The Phase 2 simulator is a lightweight deterministic digital twin created for
> hackathon development and relative controller evaluation. It is not a calibrated
> substitute for EnergyPlus.

## Problem and proposed solution

Commercial HVAC must balance comfort, indoor air quality, energy, cost, and carbon.
The future platform will compare a fixed baseline with safety-supervised,
deterministic control. Phase 2 provides the repeatable test environment required
before any controller is built.

## Simulator architecture

- `EnvironmentState`, `HVACAction`, `ZoneRuntime`, and immutable `ZoneState` records
  define boundaries between simulator components.
- `weather.py` interpolates outdoor conditions and applies time-of-use price/carbon
  schedules.
- `occupancy.py` generates independent office, conference, and lab schedules.
- `zone.py` combines thermal, humidity, CO2, and energy models.
- `building.py` owns time, independent seeded random streams, history, reset, and
  stable DataFrame export.

The building runs from 08:00 through 19:55 in 144 five-minute intervals. Three zone
records per interval produce exactly **432 records**.

## Models

### Weather

Outdoor temperature follows anchors of 25°C at 08:00, 28°C at 10:00, 31°C at
12:00, 34°C at 15:00, 29°C at 18:00, and 27°C at 20:00. Humidity is similarly
interpolated. Price is 7/10/8 INR per kWh and carbon intensity is 350/650/450
gCO2 per kWh across morning, daytime, and evening periods. Heat-wave mode adds 5°C.

### Occupancy

The office has arrival, working, lunch, afternoon, departure, and after-hours
ranges. Conference occupancy appears only in three meeting windows. The computer
lab follows four class windows. Every value is bounded by configured capacity.

### Zone physics

Temperature combines outdoor heat transfer, occupancy heat, zone equipment heat,
compressor/fan cooling, and small seeded noise. Humidity combines outdoor transfer,
occupant moisture, compressor dehumidification, and noise. CO2 combines occupant
generation with low/medium/high ventilation removal and trends toward outdoor CO2
when empty.

HVAC power is a bounded fraction of zone capacity based on positive temperature
error, fan speed, occupancy, and outdoor load. Interval energy is:

```text
interval_energy_kwh = hvac_power_kw × step_minutes / 60
```

The simulator accepts per-zone `HVACAction` objects. Missing actions use the fixed
Phase 2 Default HVAC action: 24°C, 50% fan, medium ventilation. This action is not
optimized.

## Reproducibility

Weather, occupancy, and each zone receive independent random streams derived from
the chosen seed. Seed 42 reproduces identical results; changing a seed changes noisy
values without changing structure. `reset()` recreates all streams and reproduces
the original run exactly.

## Building zones

| ID | Name | Area | Capacity | Equipment heat | HVAC capacity |
|---|---|---:|---:|---|---:|
| `office` | Open Office | 150 m² | 30 | Medium | 12 kW |
| `conference` | Conference Room | 50 m² | 12 | Low | 6 kW |
| `lab` | Computer Lab | 100 m² | 25 | High | 14 kW |

## Installation on Windows PowerShell

Python 3.11 or newer is required.

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

EnergyPlus, MCP, and Ollama remain intentionally uninstalled.

## Run

Run tests:

```powershell
pytest -q
```

Run the CLI demo and write `data/phase2_simulation.csv`:

```powershell
python -m scripts.run_phase2_demo
```

Run the Streamlit dashboard:

```powershell
streamlit run app.py
```

Choose **Phase 2 simulator validation**, optionally enable Heat Wave Scenario, and
select **Run Full-Day Simulation**. The page shows validation KPIs, latest states,
four zone charts, and a CSV download.

## Repository structure

- `config/`: validated Phase 1 settings and centralized Phase 2 coefficients
- `simulator/`: data models and implemented Phase 2 digital twin
- `scripts/`: CLI validation/export utility
- `tests/`: Phase 1 regression and Phase 2 behavioral tests
- `data/`: generated CSV destination; CSV files are ignored by Git
- `controllers/`, `prediction/`, `mcp_service/`, `llm/`,
  `energyplus_adapter/`: future boundaries only

## Known limitations and Phase 3 preview

The equations are intentionally lightweight, not calibrated against a real building,
and do not model thermal mass, solar gain, detailed airflow, latent loads, or
equipment cycling. CSV is the only optional persistence. There are no savings
claims, predictions, safety execution, database, external APIs, or real sensors.

Phase 3 will implement the fixed-schedule baseline controller against this simulator.
It is not part of the current implementation.

## Troubleshooting

- Run commands from the repository root.
- If PowerShell blocks activation, run the process-scoped execution-policy command.
- If a command is missing, activate the virtual environment and reinstall
  `requirements.txt`.
- If port 8501 is busy, run `streamlit run app.py --server.port 8502`.
