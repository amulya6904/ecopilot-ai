# Phase 12 — Hackathon demo experience

## Scope

Phase 12 is a presentation-only product layer over the accepted Phase 1–11
implementation and artifacts. It does not change EnergyPlus physics, model or
weather selection, MCP contracts, qwen3:4b agent behavior, runtime callbacks,
safety rules, comparison calculations, hashes, actuator identifiers, or
approved claims.

## Product navigation

The judge-facing routes are:

1. Command Center
2. AI Copilot
3. Building
4. Analytics
5. Decisions
6. Safety
7. EnergyPlus
8. Reports

Command Center is the default. The seven-scene Guided Demo is a hidden
registered route opened from Command Center. Developer Mode exposes Technical
Evidence, the Phase 11 alias, and all preserved legacy routes. Hidden routes
remain registered so existing page links and tests continue to work.

## Data-source modes

**Verified Demo Replay** is the default. It loads the newest valid reproducible
Phase 10 bundle plus verified Phase 7, Phase 8, and Phase 9 artifacts. It does
not call Ollama, start MCP, execute the fault suite, or start EnergyPlus during
page render.

**Live Services** is opt-in. An MCP/LLM call starts only when the user submits a
Copilot question. Read-only questions use the existing bounded MCP bridge and
Ollama client. Control questions use the existing Phase 7 advisory agent, then
run the proposal through the existing Phase 9 supervisor against a real saved
EnergyPlus telemetry state. The review has no actuator boundary and records
`actuator_write_attempted: false`; actual runtime validation remains a separate
explicit workflow.

## Evidence boundaries

- Official metrics come only from the Phase 10 summary.
- Charts come from the aligned Phase 10 CSVs and never feed calculations.
- Display downsampling retains full-resolution metric and download sources.
- Phase 7 advisory evidence is not presented as the cause of Phase 10 savings.
- The LLM-assisted Phase 8 replay is presented separately from the deterministic
  Phase 10 annual policy.
- PMV remains unavailable; occupied-temperature proxy is explicit.
- Cost and carbon are labelled as configured assumptions.
- Peak demand is described as essentially unchanged.

## Performance

JSON, selected-column CSV, and approved-download reads use `st.cache_data`
with path, file size, and modification time in the cache key. Large aligned
zone telemetry is loaded once per artifact version. Command Center reads only
the columns it displays. Current EnergyPlus API availability uses a short
30-second cache and an explicit refresh control. Chat history and guided-demo
position remain session-scoped.

## Safe failure behavior

Product pages catch artifact read failures and show the affected feature, a
safe recovery step, and collapsed diagnostics. Live Copilot timeouts and local
service failures return a public no-action message. Downloads are restricted
to the repository README, docs tree, and results tree.

## Validation

Run:

```powershell
python -m compileall .
python -m pytest -q --basetemp .pytest_tmp_phase12_final
python -m scripts.run_phase9_safety_validation
python -m scripts.run_phase10_comparison
python -m scripts.verify_phase10_reproducibility
python -m scripts.build_phase10_submission_exports
python -m streamlit run app.py
```

The dedicated Phase 12 tests can be selected with:

```powershell
python -m pytest -q tests -k phase12
```

