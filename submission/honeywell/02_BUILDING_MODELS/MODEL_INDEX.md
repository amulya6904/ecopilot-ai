# Building model index

The baseline and controlled-runtime submission files are byte-identical by
design. The controlled run uses the same frozen Phase 5 IDF and applies the
approved cooling-setpoint change through the EnergyPlus Runtime/Data Transfer
API. No separately edited “controlled” IDF is used or implied.

| Source path | Submission filename | Purpose | Classification | SHA-256 | Role | Actuator zone | Controlled parameter |
|---|---|---|---|---|---|---|---|
| `energyplus/models/baseline/phase5_baseline.idf` | `baseline_official.idf` | Frozen official annual baseline model | `official_energyplus_baseline` | `7523c515744efa4310bd40f403ebb270d649a3599ba99aa0e675e31f697b9dad` | Baseline simulation | None | Fixed schedules |
| `energyplus/models/baseline/phase5_baseline.idf` | `controlled_runtime.idf` | Frozen runtime model receiving verified API actuation | `official_energyplus_safety_supervised_controlled_evaluation` | `7523c515744efa4310bd40f403ebb270d649a3599ba99aa0e675e31f697b9dad` | Controlled simulation | `SPACE1-1` (`Open Office`) | `Zone Temperature Control / Cooling Setpoint / SPACE1-1` |

The frozen upstream telemetry-model hash recorded by both official manifests is
`5467be2c8504b32512b81320bd8500c91cecd566ec3ab9684006c18fc7229a50`.
The submitted runtime model hash is the derived Phase 5 hash shown in the
table.

Included submission-safe manifests retain hashes and experiment configuration
while replacing machine-local absolute paths with repository-relative paths.
The IDF contents have not been altered.
