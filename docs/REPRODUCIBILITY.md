# Phase 10 reproducibility

The official default control mode is deterministic. Reproduction runs:

```powershell
python -m scripts.run_phase10_controlled_evaluation
python -m scripts.run_phase10_comparison
python -m scripts.verify_phase10_reproducibility
```

The verifier repeats the annual controlled EnergyPlus run and comparison, then
checks derived-model and weather hashes, telemetry shape, facility electricity,
peak demand, occupied comfort, action count, and claim status at the frozen
comparison tolerances. It writes `reproducibility_report.json` into both
comparison bundles and updates their final/judge summaries.

LLM-assisted runs are not required to be bit-identical. They preserve the Ollama
model, prompt version, action history, and explicit limitation instead. The
official measured result uses no LLM requests.
