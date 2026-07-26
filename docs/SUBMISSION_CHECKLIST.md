# EcoPilot AI submission checklist

Status reflects repository readiness. Items requiring a human upload, URL, or
recording remain unchecked.

## Repository and source

- [ ] Add the final public GitHub repository URL to the submission portal.
- [x] Include Phase 1–11 source code.
- [x] Include `requirements.txt`.
- [x] Include the README installation and execution guide.
- [x] Preserve `.env.example`; exclude `.env`.
- [x] Include the baseline IDF:
  `energyplus/models/baseline/phase5_baseline.idf`.
- [x] Include the derived runtime IDF:
  `energyplus/models/modified/phase4_telemetry_model.idf`.
- [x] Include model/weather hashes in manifests and comparison evidence.
- [ ] Select and add an explicit open-source license if appropriate; no license
  is assumed by this checklist.

## Quantitative evidence

- [x] Quantitative dashboard is available under Phase 10.
- [x] Official baseline and controlled results use EnergyPlus.
- [x] Compatibility gate passed.
- [x] Reproducibility report passed and links to the displayed comparison.
- [x] Control injection and deterministic safety authority are verified.
- [x] Safety validation passed 22/22 scenarios.
- [x] Severe and fatal errors are zero.
- [x] Compact comparison export can be generated with
  `python -m scripts.build_phase10_submission_exports`.
- [x] Phase 11 index and manifest reference evidence without copying huge raw
  telemetry.
- [ ] Copy only the intended compact export into the final upload/ZIP and verify
  it opens on another machine.

## Documents

- [x] Submission-ready `README.md`.
- [x] `docs/SYSTEM_ARCHITECTURE.md`.
- [x] `docs/LLM_AGENT.md` and `docs/AGENT_PROMPTING.md`.
- [x] `docs/FINAL_RESULTS.md`.
- [x] `docs/DEMO_SCRIPT.md`.
- [x] `docs/PRESENTATION_OUTLINE.md`.
- [x] `docs/REPRODUCIBILITY.md`.
- [x] `results/submission/phase11/SUBMISSION_INDEX.md`.
- [x] `results/submission/phase11/submission_manifest.json`.

## Scope and claim review

- [x] Use the exact honest 5.626 kWh / 0.0096% claim.
- [x] State that the whole-building effect is small.
- [x] State that one zone is controlled conservatively.
- [x] State that peak demand is essentially unchanged.
- [x] State that PMV/PPD is unavailable and occupied temperature is the proxy.
- [x] State that cost uses INR 8/kWh and carbon uses 708 g CO₂/kWh assumptions.
- [x] State that the LLM is advisory and the final comparison policy is
  deterministic.
- [x] State that this is not a real-building deployment or production safety
  certification.
- [x] Place disclosures contextually; no standalone Limitations UI page exists.

## Demo and presentation

- [ ] Record a demonstration video of no more than three minutes.
- [ ] Add the demo-video URL to the submission portal.
- [ ] Create the final presentation from `docs/PRESENTATION_OUTLINE.md`.
- [ ] Export the presentation to the required upload format.
- [ ] Capture Home, Architecture, Phase 7, Phase 9, Phase 10, and Evidence
  screenshots at readable resolution.
- [ ] Check narration against the exact result and PMV/peak wording.
- [ ] Preload artifact pages; do not wait for annual runs or a cold model live.
- [ ] Test the Ollama-slow backup flow.

## Quality checks

- [x] Compile all Python modules.
- [x] Run the complete pytest suite.
- [x] Run Phase 9 safety validation.
- [x] Run Phase 10 comparison and reproducibility verification.
- [x] Verify every Streamlit page with the local test harness.
- [x] Confirm no expensive run starts during import or page load.
- [x] Confirm no external runtime assets, remote fonts, scripts, or CSS.
- [x] Confirm download paths remain in approved project evidence roots.
- [x] Confirm no standalone Limitations navigation item.
- [ ] Re-run the final commands after any subsequent code change.

## Security and privacy

- [x] `.env` is ignored and not exposed by the dashboard.
- [x] Source and documentation were scanned for keys, tokens, passwords,
  emails, local usernames, and absolute machine paths.
- [x] UI paths are repository-relative.
- [x] Audit evidence is preserved.
- [ ] Review generated runtime JSON for machine-local provenance before public
  upload; retain required hashes but redact paths only in a copy, never in the
  official evidence.
- [ ] Run a final sensitive-file check immediately before publishing.

## Packaging

- [ ] Confirm every intended generated artifact exists.
- [ ] Check individual file and final ZIP size against portal limits.
- [ ] Exclude virtual environments, caches, `.pytest_tmp*`, `__pycache__`,
  logs, raw annual telemetry not requested by the portal, and `.env`.
- [ ] Preserve required `.gitkeep` files, IDFs, manifests, compact exports, and
  reproducibility evidence.
- [ ] Build the final ZIP from a clean staging directory.
- [ ] Open the ZIP and verify relative paths.
- [ ] Export architecture/results documents to PDF if the portal requires PDF.
- [ ] Upload repository URL, video, presentation, screenshots, and final ZIP.
- [ ] Perform a final portal preview before submission.

## Final dashboard visual review

- [x] Apply the local warm-ivory and near-black design system.
- [x] Include the four original local SVG assets.
- [x] Verify Judge Mode contains no expensive execution buttons.
- [x] Verify Developer Mode retains Phase 2–9 explicit controls.
- [x] Verify Home, Architecture, Demo Flow, Phase 1–10, Evidence, and Checklist
  with Streamlit AppTest.
- [ ] Capture final 1920×1080, 1366×768, and narrow-width screenshots.
- [ ] Review the three final viewport captures for clipping and chart legibility.
