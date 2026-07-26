# Honeywell deliverables 1–4 index

Package scope: source documentation, building models, quantitative results,
and system architecture. GitHub is authoritative for source code; this ZIP
contains compact, reviewer-ready evidence rather than duplicate code or raw
simulation output.

| Requirement | File | Description | Source | Status |
|---|---|---|---|---|
| 1. Source code documentation | `01_SOURCE_CODE/README_SOURCE.md` | Repository, module, install, launch, test, and reproduction guide | Git repository and project README | Ready |
| 1. Source manifest | `01_SOURCE_CODE/SOURCE_MANIFEST.md` | Authoritative paths and deliberate exclusions | Repository inventory | Ready |
| 2. Official baseline model | `02_BUILDING_MODELS/baseline_official.idf` | Frozen Phase 5 EnergyPlus baseline | `energyplus/models/baseline/phase5_baseline.idf` | Ready |
| 2. Controlled runtime model | `02_BUILDING_MODELS/controlled_runtime.idf` | Same frozen IDF used with verified runtime API actuation | `energyplus/models/baseline/phase5_baseline.idf` | Ready |
| 2. Model documentation | `02_BUILDING_MODELS/MODEL_INDEX.md` | Roles, classifications, hashes, zone, and actuator parameter | Phase 5/10 manifests and runtime settings | Ready |
| 2. Weather file and setup | `02_BUILDING_MODELS/phase4_weather.epw`, `WEATHER_SETUP.md` | Included EPW, location, setup, and immutable hash | `energyplus/weather/phase4_weather.epw` | Ready |
| 2. Experiment manifests | `02_BUILDING_MODELS/*_manifest.json` | Submission-safe frozen baseline/control/model metadata | Selected Phase 10 export manifests | Ready |
| 3. Final quantitative summary | `03_QUANTITATIVE_RESULTS/final_summary.json`, `RESULTS_README.md` | Valid metrics and human-readable interpretation | Selected valid Phase 10 comparison | Ready |
| 3. Judge and executive summaries | `03_QUANTITATIVE_RESULTS/judge_summary.json`, `executive_summary.md` | Compact review material | Selected valid Phase 10 comparison | Ready |
| 3. Metric tables | `03_QUANTITATIVE_RESULTS/*_comparison.csv`, `action_summary.csv` | Energy, demand, comfort, cost, carbon, and action evidence | Selected valid Phase 10 comparison | Ready |
| 3. Validation reports | `03_QUANTITATIVE_RESULTS/*_report.json`, `safety_metrics.json`, `reliability_metrics.json` | Compatibility, reproducibility, safety, and reliability evidence | Selected valid Phase 10 comparison | Ready |
| 3. Charts | `03_QUANTITATIVE_RESULTS/charts/` | Interactive result visualizations | Selected valid Phase 10 comparison | Ready |
| 4. System architecture | `04_SYSTEM_ARCHITECTURE/SYSTEM_ARCHITECTURE.md` | Required technical architecture and trust boundaries | `docs/SYSTEM_ARCHITECTURE.md` | Ready |
| 4. Architecture guide | `04_SYSTEM_ARCHITECTURE/ARCHITECTURE_README.md` | Scope and reviewer orientation | Submission documentation | Ready |

Selected comparison:
`20260726T121750Z-phase10-comparison-956e5393`.

Validity gates: comparison valid, official EnergyPlus comparison, safety
supervisor enabled, control injection verified, telemetry alignment passed,
and independent reproducibility passed with no mismatches.
