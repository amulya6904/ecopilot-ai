# EnergyPlus Workspace

EnergyPlus is the primary final simulation engine required for official baseline
and AI closed-loop evaluation.

Phase 4 will connect the EnergyPlus executable and Python runtime/API through
`backends/energyplus.py`. The existing `energyplus_adapter/` directory is preserved,
but the backend module is the future primary application-facing adapter.

Planned layout:

- `models/baseline.idf`: future baseline building model
- `models/modified/`: future generated or runtime-modified model versions
- `weather/`: future EPW weather inputs
- `output/`: generated simulation output
- `logs/`: runtime logs and error files

No EnergyPlus functionality, IDF modification, actuator control, model, or weather
file is implemented or bundled yet. This repository does not download proprietary
or copyrighted IDF/EPW content.
