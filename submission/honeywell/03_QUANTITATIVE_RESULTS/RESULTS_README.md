# Quantitative results

Source artifact:
`results/comparison/phase10/20260726T121750Z-phase10-comparison-956e5393/final_summary.json`.
All values below are transcribed directly from that selected valid artifact.

| Result | Value |
|---|---:|
| Baseline facility electricity | 58,568.21190808615 kWh |
| Controlled facility electricity | 58,562.58583227383 kWh |
| Absolute energy reduction | 5.626075812324416 kWh |
| Percentage energy reduction | 0.009606022839067856% |
| Baseline occupied-temperature compliance | 23.225357018460464% |
| Controlled occupied-temperature compliance | 23.39254615116684% |
| Comfort change | +0.16718913270637614 percentage points |
| Baseline peak demand | 21.050576908787157 kW |
| Controlled peak demand | 21.050577252463818 kW |
| Peak-demand reduction | -0.0000003436766604636432 kW (-0.0000016326234760824155%); effectively unchanged |
| Cost reduction | INR 45.00860649859533 |
| Carbon reduction | 3.983261675130052 kg CO₂ |
| Severe error count | 0 |
| Fatal error count | 0 |
| Comparison validity | `true` |
| Telemetry alignment | `true`; 8,760/8,760 facility intervals, 100.0% |
| Safety supervisor enabled | `true` |
| Actuator injection verified | `true` |

Approved statement from the artifact:

> Under the documented compatible EnergyPlus experiment, the
> safety-supervised controlled run reduced facility electricity by 5.626 kWh
> (0.010%) while meeting the configured occupied comfort gate.

PMV is unavailable in the retained EnergyPlus model; occupied-temperature
proxy compliance is reported instead.

Cost and carbon values are derived from configured assumptions and are not
direct EnergyPlus outputs.

The comparison is an official EnergyPlus, safety-supervised, one-zone,
deterministic-policy experiment. It is reproducible within the configured
`1e-6` tolerance, with matching model/weather hashes, telemetry shape, actions,
status, energy, peak-demand, and comfort results.
