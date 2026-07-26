# Legacy EnergyPlus Adapter Boundary

This pre-existing package is preserved for compatibility. EnergyPlus integration is
not implemented.

`backends/energyplus.py` is now the planned primary application-facing adapter for
Phase 4. It will eventually map EnergyPlus runtime telemetry, errors, and actuators
to the shared backend schemas. The current class is an explicitly unavailable
placeholder and does not execute EnergyPlus or modify IDFs.
