# Phase 10 quantitative comparison

Phase 10 compares an official fixed-schedule EnergyPlus baseline with a compatible
safety-supervised controlled EnergyPlus run. Savings are reported only when model,
weather, period, occupancy, reporting, and telemetry compatibility checks pass
and the configured occupied-temperature proxy does not degrade. Lightweight
development-simulator results are not used for official savings claims.

## Experiment

The baseline is the Phase 5 annual fixed-schedule artifact. The controlled case
uses the identical derived IDF, EPW, EnergyPlus 26.1.0 engine, annual run period,
occupancy/internal-load/HVAC configuration, output requests, hourly reporting,
and initial conditions. Only the verified `SPACE1-1` cooling-setpoint control
strategy differs.

The default `reproducible_policy` checks live occupancy, zone temperature, current
setpoint, and facility demand hourly. When demand is at least 18 kW but below the
30 kW critical threshold and the occupied zone has 0.5°C comfort headroom, it
requests a 0.5°C cooling-setpoint increase. Phase 9 evaluates every request.
Otherwise the actuator is held or reset to the Phase 5 schedule.

## Gates

The compatibility report includes every pass and failure for backend/source,
classification, success, base/derived model hashes, weather hash, EnergyPlus
version, run period, reporting, occupancy, internal loads, zone mapping, expected
intervals, telemetry, diagnostics, control injection, and safety authority.

Facility telemetry is aligned one-to-one by hourly timestamp; zone telemetry is
aligned by timestamp and EnergyPlus zone name. Missing or duplicate records make
the comparison incomplete. Official metrics are not calculated for a failed
compatibility or required-alignment gate.

## Outputs

`results/comparison/phase10/<comparison-id>/` contains strict JSON summaries,
comparison CSVs, aligned telemetry, action history, reliability/agent/safety
metrics, reproducibility evidence, executive summary, manifest hashes, and
unit-labelled charts. NaN becomes JSON null. Facility energy is never joined to
and duplicated across zone rows.

## Verified result and interpretation

The reproducible comparison measured 58,568.21190808615 kWh for the baseline
and 58,562.58583227383 kWh for the controlled case: a difference of
5.626075812324416 kWh, or 0.009606022839067856%. Occupied-temperature proxy
compliance improved by 0.16718913270637614 percentage points, while peak demand
was essentially unchanged.

Genuine PMV/PPD is unavailable in the retained People objects. Cost and carbon
are derived using the configured INR 8/kWh tariff and 708 g CO₂/kWh carbon
intensity. This is a conservative one-zone proof of concept, not a
real-building deployment or production safety certification.

## Executive results page

The Phase 10 page reads the newest valid reproducible bundle and never starts a
comparison on navigation. It shows exact final cumulative-energy endpoints,
peak demand as essentially unchanged, occupied-temperature proxy metrics with
PMV unavailable, deterministic safety outcomes, and fallback/rollback evidence.
The action-to-impact table displays 24 meaningful windows ranked by absolute
interval-energy difference; the complete joined table and source CSVs remain
downloadable. Tariff and carbon values are visibly labelled as configured
assumptions.
