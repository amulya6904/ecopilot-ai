# Phase 11 submission index

This index references existing source and verified evidence. It does not duplicate large annual telemetry.

Displayed Phase 10 comparison: `20260726T095346Z-phase10-comparison-fefa0655`

| File | Purpose | Source phase | Classification | Required | Recommended upload format |
|---|---|---|---|:---:|---|
| `README.md` | Project overview, setup, measured result, scope, and evidence guide | Phase 11 | submission_document | Yes | Markdown / repository landing page |
| `requirements.txt` | Pinned project dependency entry point | Phase 1–11 | source_dependency_manifest | Yes | Text |
| `app.py` | Offline Streamlit dashboard entry point | Phase 11 | source_code | Yes | Repository source |
| `energyplus/models/baseline/phase5_baseline.idf` | Official fixed-schedule EnergyPlus baseline model | Phase 5 | official_energyplus_baseline_model | Yes | IDF |
| `energyplus/models/modified/phase4_telemetry_model.idf` | Derived telemetry/runtime EnergyPlus model | Phase 4–8 | energyplus_runtime_model | Yes | IDF |
| `results/official/phase5_energyplus_baseline_manifest.json` | Frozen baseline model, weather, source, and output evidence | Phase 5 | official_energyplus_baseline_manifest | Yes | JSON |
| `docs/SYSTEM_ARCHITECTURE.md` | Required architecture report and trust boundaries | Phase 11 | submission_document | Yes | Markdown and optional PDF |
| `docs/LLM_AGENT.md` | Local model, prompt, tool, timeout, and fallback design | Phase 7 / 11 | submission_document | Yes | Markdown and optional PDF |
| `docs/FINAL_RESULTS.md` | Exact result interpretation and contextual assumptions | Phase 10 / 11 | submission_document | Yes | Markdown and optional PDF |
| `docs/DEMO_SCRIPT.md` | Three-minute judge demo script and backup flow | Phase 11 | submission_document | Yes | Markdown |
| `docs/PRESENTATION_OUTLINE.md` | Fourteen-slide presentation content | Phase 11 | submission_document | Yes | Markdown; convert to PPTX/PDF manually |
| `docs/SUBMISSION_CHECKLIST.md` | Final human and automated packaging checks | Phase 11 | submission_document | Yes | Markdown |
| `results/comparison/phase10/20260726T095346Z-phase10-comparison-fefa0655/final_summary.json` | Exact official comparison result and claim gate | Phase 10 | official_energyplus_quantitative_comparison | Yes | JSON |
| `results/comparison/phase10/20260726T095346Z-phase10-comparison-fefa0655/comparison_manifest.json` | Comparison file hashes and provenance | Phase 10 | official_energyplus_comparison_manifest | Yes | JSON |
| `results/comparison/phase10/20260726T095346Z-phase10-comparison-fefa0655/reproducibility_report.json` | Repeatability relationship for the displayed comparison | Phase 10 | deterministic_reproducibility | Yes | JSON |
| `results/comparison/phase10/20260726T095346Z-phase10-comparison-fefa0655/submission_export-20260726T095357Z/submission_export_manifest.json` | Compact judge-facing comparison export; raw annual telemetry omitted | Phase 10 | submission_export | Yes | ZIP when available; otherwise Markdown |
| `results/safety/phase9/20260726T095238Z-phase10-reproducible_policy-c610f70b/run_metadata.json` | Latest Phase 9 safety-validation run metadata | Phase 9 | safety_supervised_energyplus_runtime_validation | Yes | JSON |
| `results/agent/phase7/20260726T095104Z-705dd78b/run_metadata.json` | Latest local qwen3:4b advisory run evidence | Phase 7 | llm_advisory_proposal | Yes | JSON |

## Packaging note

Upload only the files required by the portal. Keep official artifacts unchanged; if machine-local provenance must be redacted for publication, create a clearly labeled copy.

Human-only deliverables still required: public repository URL, three-minute video, final presentation export, screenshots, license decision, and portal upload verification.
