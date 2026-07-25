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

Phase 4 provides verified EnergyPlus execution, diagnostics, zone and outdoor
temperature telemetry, facility electricity, and facility peak-demand telemetry.
It does not implement an official fixed-schedule EnergyPlus baseline, actuator
injection, MCP, LLM reasoning, optimization, or closed-loop control.
