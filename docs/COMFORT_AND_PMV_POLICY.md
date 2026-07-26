# Comfort and PMV Policy

Phase 9 has two explicit comfort modes.

## Genuine PMV/PPD

`pmv_ppd` is used only when a genuine EnergyPlus Runtime API PMV value is present.
Occupied PMV must remain from -0.5 to 0.5. An action cannot relax cooling while PMV
is already hot, or increase cooling while PMV is already cold. PPD above 20% is a
prototype warning; above the configured critical policy after an action requires
rollback.

## Occupied-temperature proxy

`occupied_temperature_proxy` is used when PMV is absent and proxy use is enabled.
The occupied range is 22–25 °C. The evaluator checks current compliance, distance
to the relevant boundary, action direction, and available comfort headroom.
Unoccupied limits are wider and explicitly distinct.

The retained Phase 5 model requests PMV/PPD outputs but its People objects do not
enable the Fanger model. Runtime handles therefore remain unavailable. Phase 9
records `PMV_UNAVAILABLE_USING_TEMPERATURE_PROXY`, sets PMV availability false, and
does not estimate or fabricate PMV from temperature.

These prototype constraints are not an ASHRAE certification or a production
building safety guarantee.
