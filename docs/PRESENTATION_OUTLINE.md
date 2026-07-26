# Presentation outline

## Slide 1 — EcoPilot AI

- **Key message:** Safety-supervised autonomous EnergyPlus building control can
  be local, typed, auditable, and evidence-backed.
- **Visual:** Title over the six-block system overview from Home.
- **Evidence:** EnergyPlus, MCP, qwen3:4b, safety, actuator, comparison badges.
- **Speaker note:** Lead with the trust boundary and call this a conservative
  single-zone proof of concept.

## Slide 2 — The problem

- **Key message:** Energy optimization is not useful if it weakens comfort,
  safety, reliability, or evidence quality.
- **Visual:** Four constraints around an HVAC actuator: energy, comfort, safety,
  explainability.
- **Evidence:** Compatibility gate and Phase 9 rule categories.
- **Speaker note:** Explain why both physical simulation and deterministic
  final authority are required.

## Slide 3 — Why existing BMS is insufficient

- **Key message:** Fixed schedules are predictable but cannot reason over new
  evidence; unconstrained AI is flexible but cannot be trusted with actuators.
- **Visual:** Fixed schedule ↔ bounded advisory ↔ deterministic control.
- **Evidence:** Phase 5 thermostat adherence and Phase 7 advisory-only flags.
- **Speaker note:** Position EcoPilot as an augmentation architecture, not a
  replacement for engineered safety.

## Slide 4 — Solution overview

- **Key message:** EcoPilot connects an EnergyPlus digital twin to local
  intelligence through typed and supervised boundaries.
- **Visual:** Six core Home-page blocks.
- **Evidence:** Verified status cards for integration, tools, LLM, injection,
  safety, and comparison.
- **Speaker note:** Mention fully local runtime operation and classified
  artifacts.

## Slide 5 — Architecture

- **Key message:** Every transition has an explicit responsibility and trust
  level.
- **Visual:** The Architecture page's end-to-end flow.
- **Evidence:** Layer table and trust-boundary statement.
- **Speaker note:** State verbatim that the LLM never writes directly to an
  EnergyPlus actuator.

## Slide 6 — MCP and LLM autonomy

- **Key message:** qwen3:4b receives bounded official evidence and returns only
  a compact typed advisory decision.
- **Visual:** MCP tool catalogue → two-message prompt → five-field JSON.
- **Evidence:** Phase 6 audit, Phase 7 run metadata, decision, validation.
- **Speaker note:** Thinking is disabled; outputs are bounded; latency is
  hardware-dependent; no hidden chain-of-thought is used.

## Slide 7 — Safe closed loop

- **Key message:** Deterministic validation and Phase 9 own final authority.
- **Visual:** Candidate → approve/clamp/hold/reject → write or baseline fallback.
- **Evidence:** Safety rule inventory and decision counts.
- **Speaker note:** Clarify that the annual reproducible policy uses the same
  safety and actuator boundaries without callback-time inference.

## Slide 8 — EnergyPlus actuator proof

- **Key message:** The project performs and observes a real Data Transfer API
  cooling-setpoint write.
- **Visual:** `Zone Temperature Control | Cooling Setpoint | SPACE1-1`.
- **Evidence:** Actuator inventory, action IDs, applied/observed setpoints,
  control-injection and reset verification.
- **Speaker note:** Emphasize exact handle discovery and post-action
  verification.

## Slide 9 — Safety and fault injection

- **Key message:** Unsafe state is handled deliberately, not hidden.
- **Visual:** 22/22 matrix across all six outcomes.
- **Evidence:** Phase 9 validation summary, fallback/rollback events, zero
  severe/fatal errors.
- **Speaker note:** Demand limits are prototype guardrails and this is not
  production safety certification.

## Slide 10 — Quantitative results

- **Key message:** The compatible annual experiment produces a small positive
  energy result without proxy degradation.
- **Visual:** Baseline/controlled KPIs and cumulative-electricity chart.
- **Evidence:** 58,568.211908 vs 58,562.585832 kWh; 5.626076 kWh or
  0.009606%; +0.167 percentage points; peak essentially unchanged.
- **Speaker note:** Use the exact approved claim. Do not round 0.0096% up or call
  peak demand a reduction.

## Slide 11 — Result interpretation

- **Key message:** A small whole-building effect is expected from one
  conservatively controlled zone.
- **Visual:** One highlighted zone inside a six-zone/whole-facility boundary.
- **Evidence:** Controlled-zone identity, action count, proxy method, violation
  counts.
- **Speaker note:** PMV/PPD is genuinely unavailable; occupied temperature is
  the explicit proxy.

## Slide 12 — Business value

- **Key message:** The reusable value is the governance pattern: simulation,
  bounded AI, deterministic authority, audit, and claim gating.
- **Visual:** Evidence chain from proposal to reproducible comparison.
- **Evidence:** Classified artifacts, project-scoped downloads, compatibility
  and reproducibility reports.
- **Speaker note:** Cost and carbon are derived assumptions, not promises of
  production savings.

## Slide 13 — Future roadmap

- **Key message:** Scale only after evidence quality and safety boundaries
  remain intact.
- **Visual:** Multi-zone → native PMV → site calibration → read-only shadow
  pilot.
- **Evidence:** Current design-scope disclosures and future-work list.
- **Speaker note:** Include faster local hardware, additional buildings/weather,
  real tariff/carbon data, and commissioned thresholds.

## Slide 14 — Closing

- **Key message:** EcoPilot AI proves that local autonomy can be useful without
  bypassing building-control discipline.
- **Visual:** Three final badges: real actuator, deterministic safety,
  reproducible evidence.
- **Evidence:** Control injection verified, 22/22 safety, reproducible Phase 10.
- **Speaker note:** Close with the honest 5.626 kWh result and invite judges to
  inspect the evidence page.
