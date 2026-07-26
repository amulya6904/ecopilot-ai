# Final verified results

## Approved claim

> Under a fully aligned and reproducible EnergyPlus experiment, the
> safety-supervised one-zone control policy reduced annual facility electricity
> by approximately 5.626 kWh, or 0.0096%. Occupied-temperature proxy compliance
> improved slightly relative to the fixed-schedule baseline, while peak demand
> remained effectively unchanged.

The measured whole-building effect is small because this proof of concept
controls one zone conservatively under strict safety constraints.

## Preserved metrics

| Metric | Value |
|---|---:|
| Baseline facility electricity | 58,568.21190808615 kWh |
| Controlled facility electricity | 58,562.58583227383 kWh |
| Absolute electricity reduction | 5.626075812324416 kWh |
| Percentage electricity reduction | 0.009606022839067856% |
| Baseline peak demand | 21.050576908787157 kW |
| Controlled peak demand | 21.050577252463818 kW |
| Absolute peak reduction | -0.000000343676660464 kW |
| Baseline occupied-temperature compliance | 23.225357018460464% |
| Controlled occupied-temperature compliance | 23.39254615116684% |
| Comfort-proxy change | +0.16718913270637614 percentage points |
| Baseline low/high violations | 11,014 / 7 |
| Controlled low/high violations | 10,990 / 7 |
| Derived cost reduction | INR 45.00860649859533 |
| Derived carbon reduction | 3.983261675130052 kg CO₂ |
| Severe / fatal errors | 0 / 0 |

Peak demand is **essentially unchanged**. The absolute difference is within the
`1e-6` reproducibility tolerance and must not be described as a meaningful peak
reduction.

## Comfort interpretation

Configured occupied-temperature proxy did not degrade relative to baseline.
The absolute compliance level is shown because the percentage remains modest.
Genuine PMV/PPD is unavailable in the retained EnergyPlus People objects;
neither PMV nor a PMV-derived compliance value is fabricated.

## Experiment validity

- Both runs use EnergyPlus 26.1.0.
- Base and derived model hashes match.
- Weather hashes match.
- Annual period and hourly reporting match.
- Occupancy, loads, and zone mapping match.
- All 8,760 facility intervals align.
- All 52,560 zone records align.
- Control injection is verified.
- The deterministic safety supervisor is enabled.
- The displayed comparison is the verified repeat in its reproducibility report.
- Severe and fatal errors are zero.

## Component meters

The report uses exact EnergyPlus meter names:

| Display | Source | Conversion |
|---|---|---|
| Facility electricity meter | `Electricity:Facility` | hourly J to kWh |
| HVAC electricity meter | `Electricity:HVAC` | hourly J to kWh |
| Cooling electricity meter | `Cooling:Electricity` | hourly J to kWh |
| Heating electricity meter | `Heating:Electricity` | hourly J to kWh |
| Fan electricity meter | `Fans:Electricity` | hourly J to kWh |

In the retained model, `Electricity:HVAC` equals `Fans:Electricity`; they are
shown independently and are not summed.

## Assumptions and technical scope

- Only `SPACE1-1` is controlled.
- The annual comparison policy is deterministic; qwen3:4b is demonstrated as a
  separate bounded advisory capability.
- PMV/PPD is unavailable, so occupied temperature is the declared proxy.
- Cost uses a flat INR 8/kWh project assumption.
- Carbon uses a constant 708 g CO₂/kWh project assumption.
- Demand thresholds are prototype guardrails.
- This is not a real-building deployment or production safety certification.
- Future work includes multi-zone coordination, native PMV inputs, site
  calibration, more weather years, and a read-only building shadow pilot.

Full precision remains in the Phase 10 JSON and CSV artifacts.
