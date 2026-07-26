# EcoPilot AI three-minute guided demo

## Before recording

- Start the app with `python -m streamlit run app.py`.
- Leave **Judge Mode** enabled and **Developer Mode** disabled.
- Keep the data source on **Verified Demo Replay**.
- Open **Command Center** and select **Start guided demo**.
- Use the saved Phase 7–10 evidence; do not start EnergyPlus, MCP validation,
  or a cold Ollama request during the recording.
- Record at 1920×1080 or 1366×768 with the sidebar expanded.

Verified Demo Replay is deterministic and does not require Ollama. It is
labelled as artifact replay throughout and is never described as a currently
running EnergyPlus process.

## 0:00–0:25 — Scene 1: Command Center

**Say:** “EcoPilot AI connects official EnergyPlus evidence to bounded MCP
tools, a local qwen3:4b advisory, deterministic validation, and final safety
authority. This is a verified artifact replay of the complete system.”

Point to EnergyPlus verified, MCP ready, the saved qwen3:4b response, active
safety, verified actuator, 22/22 scenarios, and the exact 5.626 kWh result.

## 0:25–0:45 — Scene 2: Telemetry

**Say:** “The selected state comes from aligned EnergyPlus telemetry.
`SPACE1-1` is the only controlled cooling-setpoint zone; all other zones are
monitored only.”

Point to timestamp, indoor temperature, occupancy, setpoint, and source.

## 0:45–1:10 — Scene 3: AI Copilot

**Say:** “The saved qwen3:4b advisory used five bounded MCP tools and returned a
typed proposal with an explicit reason. It remained advisory and was not
applied.”

Show the proposal fields and MCP tool names. Do not describe hidden
chain-of-thought. If demonstrating the full Copilot page, use a suggested
replay question.

## 1:10–1:35 — Scene 4: Safe Decision

**Say:** “In the separate verified LLM-assisted runtime replay, deterministic
direction validation rejected the raw candidate, selected the safe fallback,
wrote the EnergyPlus actuator, observed the result, and reset to baseline.”

Keep this replay distinct from the deterministic Phase 10 annual savings run.

## 1:35–1:55 — Scene 5: Unsafe Action

**Say:** “An unknown-zone proposal is rejected by the existing Phase 9 safety
supervisor before actuator access. The baseline or last-known-safe state remains
protected.”

Optionally open Safety and select **Test Unsafe Proposal**. The interaction
runs only the in-memory deterministic fault suite and has no actuator handle.

## 1:55–2:35 — Scene 6: Analytics

**Say:** “The compatible annual comparison aligns 8,760 hourly intervals.
Controlled electricity was 58,562.585832 kilowatt-hours—5.626076
kilowatt-hours, or 0.009606 percent, below baseline. The configured
occupied-temperature proxy changed by plus 0.167 percentage points, while peak
demand remained essentially unchanged.”

Show cumulative energy. If time permits, open Analytics to show demand,
comfort bounds, setpoints, action lifecycle, safety/fallback, cost, and carbon.
Metrics use full-resolution data; chart aggregation is display-only.

## 2:35–3:00 — Scene 7: Closing

**Say:** “The whole-building effect is intentionally small because one zone is
controlled conservatively under strict safety limits. PMV was unavailable.
Cost and carbon use configured assumptions. The reusable result is the
governed, auditable path from physical evidence to safe action.”

Point to the approved comparison statement, 22/22 safety result, and zero
severe/fatal errors.

## Backup flow

1. Stay in Verified Demo Replay.
2. If Ollama is unavailable, use suggested Copilot questions; they answer only
   from saved artifacts and clearly identify their sources.
3. If a saved artifact is missing, show the safe empty state and recovery step;
   do not replace it with sample data.
4. Never restart Ollama, run an annual baseline, rerun the controlled year, or
   execute reproducibility during the recording.
5. Keep the exact small-result, temperature-proxy, and unchanged-peak wording.
