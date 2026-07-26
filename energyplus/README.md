# EnergyPlus Workspace

Phase 4 is verified with EnergyPlus 26.1 using:

- base IDF: `models/base/phase4_base_model.idf`
- derived IDF: `models/modified/phase4_telemetry_model.idf`
- weather: `weather/phase4_weather.epw`
- raw runs: `output/official/<run-id>/`
- metadata: `metadata/<run-id>.json`

The base IDF is never overwritten. `adapter/output_requests.py` creates the derived
IDF with an EcoPilot header and avoids duplicate requests. It adds hourly Zone Mean
Air Temperature, Facility Total Electricity Demand Rate, Electricity:Facility, and
Electricity:HVAC requests plus Output:SQLite. The source model's existing hourly
Site Outdoor Air Drybulb Temperature request is reused.

Verified EnergyPlus 26.1 columns:

- `Electricity:Facility [J](Hourly)`
- `Electricity:HVAC [J](Hourly)`
- `Whole Building:Facility Total Electricity Demand Rate [W](Hourly)`
- `Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)`
- `<ZONE>:Zone Mean Air Temperature [C](Hourly)`

Facility electricity is converted with J / 3,600,000. Facility demand is direct and
converted with W / 1,000. Building telemetry has one row per timestamp and is not
repeated or summed across zone rows. PMV and CO2 remain unavailable.

The accepted non-fatal warning is classified `weather_location_mismatch`: the
official example IDF declares Chicago while the configured EPW is Bengaluru.
EnergyPlus explicitly uses the EPW location. The full message and classification
are retained in each run's metadata. Verified runs have zero severe and fatal
errors.

## Phase 5 fixed-schedule baseline

Option A retains the verified Phase 4 example model and derives:

- source: `models/modified/phase4_telemetry_model.idf`
- baseline: `models/baseline/phase5_baseline.idf`
- raw baseline runs: `output/official/baseline/<run-id>/`
- runner metadata: `metadata/baseline/<run-id>.json`
- stable official artifacts: `../results/official/phase5_*`

The object-level builder retargets only the three thermostat-setpoint objects shared
by the five conditioned zones. It does not rename zones or change geometry, HVAC
topology, People, Lights, ElectricEquipment, sizing, ventilation, or availability
schedules.

| Technical zone | Display alias | Comfort treatment |
|---|---|---|
| `SPACE1-1` | Open Office | included |
| `SPACE2-1` | Conference Room | included |
| `SPACE3-1` | Computer Lab | included |
| `SPACE4-1` | Support Zone | included |
| `SPACE5-1` | Auxiliary Zone | included |
| `PLENUM-1` | HVAC Plenum | raw telemetry only; excluded |

Cooling is 27°C before 09:00, 22°C from 09:00–18:00, and 27°C afterward.
Heating is 16°C before 09:00, 20°C from 09:00–18:00, and 16°C afterward.
At hourly reporting frequency, the EnergyPlus timestamp is the interval end, so the
09:00 record contains the value for the interval ending at 09:00.

Frozen SHA-256 values:

- Phase 4 source:
  `5467be2c8504b32512b81320bd8500c91cecd566ec3ab9684006c18fc7229a50`
- Phase 5 derived model:
  `7523c515744efa4310bd40f403ebb270d649a3599ba99aa0e675e31f697b9dad`
- EPW:
  `b24506e034c43d31950862232b97b404e573de4c8bee04204f62d0890bcae478`

Actual hourly baseline output includes facility/HVAC/cooling/heating/fan
electricity, direct facility demand, zone/outdoor temperature, cooling/heating
setpoints, People occupancy, and relative humidity. Fanger PMV/PPD is explicitly
unavailable because the retained People objects do not enable those models. The
request is kept in the IDF and its non-fatal reporting warning proves that null
handling is honest.

The manifest records model/weather hashes, EnergyPlus version, executable, run
period, reporting frequency, load schedules, thermostat policy, zone mapping,
requested/actual outputs, and warnings. `--verify-reproducibility` performs two
real runs and compares identities, telemetry shapes, diagnostics, electricity,
peak demand, adherence, and comfort metrics.

Phase 5 establishes the official fixed-schedule EnergyPlus baseline using the
existing verified EnergyPlus example model. Original EnergyPlus zone identifiers
are preserved, while display aliases are used for presentation. This phase does
not implement MCP, an open-source LLM, actuator injection, autonomous control,
optimization, or savings comparison.

## Phase 6 MCP access

Phase 6 exposes Phase 4 readiness and persisted Phase 5 official artifacts through
a local official-SDK `mcp==1.28.1` stdio server. It reuses EnergyPlus discovery,
the baseline runner, normalized telemetry, metrics, manifest, and diagnostics.
It does not add runtime callbacks or modify actuators, schedules, or setpoints.

Run `python -m scripts.test_phase6_mcp_client` for an SDK-level smoke test. Add
`--run-baseline` only when a new controlled official execution is intended.
