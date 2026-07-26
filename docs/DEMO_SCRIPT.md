# Three-minute demo script

## Before recording

- Start Ollama beforehand and confirm `ollama ps` shows `qwen3:4b`; do not run
  `ollama serve` again.
- Start Streamlit with `python -m streamlit run app.py`.
- Enable **Judge mode** in the sidebar.
- Preload Home, Architecture, Phase 5, Phase 7, Phase 9, and Phase 10.
- Keep the latest Phase 7 advisory artifacts and the passing Phase 9/10
  artifacts available.
- Do not start an annual EnergyPlus run or wait for a cold local model during
  the recording.

## 0:00–0:20 — Problem and objective

**Click:** Overview → Home.

**Say:** “Building controls must reduce energy without handing an unpredictable
model direct HVAC authority. EcoPilot AI combines an EnergyPlus digital twin,
bounded local intelligence, deterministic safety, and auditable actuator
control.”

Point to the six system blocks and verified-status cards.

## 0:20–0:40 — Architecture overview

**Click:** Overview → Architecture.

**Say:** “Telemetry flows from EnergyPlus through local MCP evidence to
qwen3:4b. The model returns a typed proposal, but deterministic validation and
the Phase 9 safety supervisor retain final authority before actuator injection,
observation, and fallback.”

Point to the trust-boundary statement. Do not imply that the LLM directly
controls EnergyPlus.

## 0:40–1:00 — Official EnergyPlus baseline

**Click:** Official EnergyPlus pipeline → Phase 5.

**Say:** “The official fixed-schedule baseline is a complete annual EnergyPlus
26.1 run: 8,760 hourly facility intervals, frozen model and weather hashes, and
58,568.211908 kilowatt-hours.”

Use the pre-generated manifest. Do not click the baseline-run button.

## 1:00–1:25 — MCP tools and local qwen3:4b proposal

**Click:** Phase 6, then Phase 7.

**Say:** “Sixteen bounded MCP tools expose classified official evidence over
local stdio. qwen3:4b runs locally with thinking disabled and emits a very small
schema. It is advisory only and has no direct actuator authority.”

Show the latest pre-generated advisory result. Avoid a live call unless the
model is already warm and time is available.

## 1:25–1:50 — Safety validation and actuator injection

**Click:** Phase 9, then Phase 8 if time permits.

**Say:** “Every candidate passes deterministic comfort, demand, freshness,
change-rate, oscillation, and actuator checks. The verified write target is the
SPACE1-1 cooling setpoint, with later observation and reset.”

Point to 22/22 safety scenarios, all decision outcomes, and zero severe/fatal
errors.

## 1:50–2:10 — Unsafe action rejected and fallback

**Click:** Phase 9 fault results.

**Say:** “Unsafe, stale, oscillating, or mismatched actions are held, rejected,
rolled back, or sent to emergency fallback. The fixed Phase 5 schedule is the
safe default.”

Use pre-generated fault evidence; do not run fault injection live.

## 2:10–2:40 — Official Phase 10 comparison

**Click:** Phase 10.

**Say:** “The compatibility gate aligns the same model, weather, period, and
8,760 hourly intervals. The one-zone policy reduced annual facility electricity
by 5.626 kilowatt-hours, or 0.0096 percent. The configured temperature proxy
improved by 0.167 percentage points, and peak demand is essentially unchanged.”

Point to the exact claim, KPI cards, comfort method, and reproducibility chain.

## 2:40–3:00 — Interpretation and future work

**Click:** Home, Scope and assumptions.

**Say:** “The result is intentionally modest: one zone, conservative safety
constraints, and a whole-building meter. This is a proof of concept, not a
deployment or safety certification. Next steps are multi-zone coordination,
native PMV evidence, site calibration, and a read-only building shadow pilot.”

## Backup plan if Ollama is slow

1. Do not restart Ollama during the presentation.
2. Stop any live Phase 7 attempt if it threatens the timeline.
3. Show the latest `results/agent/phase7/<run-id>/run_metadata.json`,
   `llm_decision.json`, and `validation.json` through the preloaded page.
4. State: “Local inference latency is hardware-dependent; this recorded,
   classified result used the same compact schema and official MCP evidence.”
5. Continue to Phase 9 and Phase 10. The final quantitative comparison is
   deterministic and does not depend on a live LLM call.

## What never to wait for live

- a full annual EnergyPlus baseline;
- a full annual controlled run;
- the reproducibility repeat;
- all Phase 9 fault-injection scenarios;
- a cold qwen3:4b model load.

All five have persisted evidence and explicit rerun commands.
