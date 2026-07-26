# EcoPilot AI Phase 10 executive summary

## Result

Under the documented compatible EnergyPlus experiment, the safety-supervised controlled run reduced facility electricity by 5.626 kWh (0.010%) while meeting the configured occupied comfort gate.

## Experiment identity

- Baseline run: `20260726T072047Z-29380aea`
- Controlled run: `20260726T121644Z-phase10-reproducible_policy-3edee0c3`
- Control mode: `reproducible_policy`
- Compatibility: `comparable`
- Backend/source: EnergyPlus / EnergyPlus
- Safety authority: deterministic Phase 9 supervisor

## Measured metrics

- Baseline facility electricity: 58568.21190808615 kWh
- Controlled facility electricity: 58562.58583227383 kWh
- Energy reduction: 5.626075812324416 kWh
- Energy reduction percentage: 0.009606022839067856%
- Baseline peak demand: 21.050576908787157 kW
- Controlled peak demand: 21.050577252463818 kW
- Baseline occupied comfort: 23.225357018460464%
- Controlled occupied comfort: 23.39254615116684%
- Severe/fatal errors: 0/0

## Claim decision

- Status: `validated_positive_savings`
- Eligible to claim savings: `true`

Cost and carbon are derived from the documented Phase 10 tariff and grid-intensity assumptions; they are not raw EnergyPlus outputs.
