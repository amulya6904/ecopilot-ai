# EcoPilot AI system architecture

## Purpose and verified scope

EcoPilot AI is an EnergyPlus-first, local, safety-supervised proof of concept.
It demonstrates bounded evidence retrieval, a typed local-LLM advisory path, a
real runtime actuator write, deterministic final authority, post-action
verification, fault recovery, and a reproducible annual comparison.

The retained experiment controls the `SPACE1-1` cooling setpoint in an example
EnergyPlus model. It is not a real-building deployment, a production optimizer,
or a safety-certified controller. Genuine PMV/PPD is unavailable in the
retained People objects; occupied-temperature compliance is the declared proxy.

## End-to-end flow

```text
EnergyPlus 26.1
  → runtime/data-transfer telemetry
  → bounded local MCP tools
  → local qwen3:4b advisory inference
  → compact typed proposal
  → deterministic proposal validation
  → Phase 9 safety supervisor
  → discovered cooling-setpoint actuator
  → post-action observation
  → reset / fallback / rollback
  → compatible, aligned Phase 10 comparison
  → classified evidence and submission dashboard
```

### Trust boundary

> The LLM never writes directly to an EnergyPlus actuator. All proposals are
> converted into typed candidates and must pass deterministic validation and
> safety supervision.

The Phase 9 supervisor is the final authority. The annual quantitative result
uses a deterministic one-zone policy so the controlled run can be reproduced
without placing local-model inference in the EnergyPlus callback path.

## 1. EnergyPlus-first design

EnergyPlus supplies official building physics, weather response, schedules,
equipment behavior, zone state, meters, warnings, and runtime callbacks. The
lightweight simulator remains a development tool and is never used for the
official Phase 10 savings claim.

The Phase 5 baseline freezes:

- EnergyPlus version;
- immutable base-model and derived-model SHA-256 hashes;
- weather SHA-256 hash;
- annual run period and reporting frequency;
- occupancy, internal-load, and zone-mapping fingerprints;
- available telemetry and error counts.

The compatible controlled run executes the same derived Phase 5 model and
weather file.

## 2. Backend abstraction

The project backend interface separates development simulation from official
EnergyPlus execution. Backend status and artifact classification travel with
results, preventing a lightweight result from being relabeled as official.
EnergyPlus runners are explicit commands, not import-time or page-load side
effects.

## 3. MCP communication layer

The local MCP server uses stdio and exposes bounded tools and resources for:

- system and EnergyPlus readiness;
- official baseline summary and manifest;
- latest run metadata;
- zone and facility telemetry;
- comfort and thermostat evidence;
- available outputs and runtime errors.

The default tool surface is read-only. A separately gated baseline runner is
the only execution-class operation; no MCP actuator or optimization tool
exists. Tool requests, classifications, timing, and bounded results are written
to the audit log.

### Tool-result bounding

Telemetry tools accept date/aggregation/row limits. The bridge applies an
allowlist and character bounds before evidence enters model context. The model
receives compact summaries rather than raw annual CSVs. Required evidence is
retrieved through a deterministic plan in the live CPU path, which removes an
unnecessary tool-selection inference round while preserving MCP provenance.

## 4. Local LLM advisory layer

Ollama serves `qwen3:4b` locally. Remote model providers and non-local Ollama
hosts are rejected by settings validation.

The advisory prompt has two logical stages:

1. a stable system contract defining advisory scope, evidence requirements,
   prohibited claims, and output semantics;
2. a compact evidence prompt containing only the official facts needed for a
   decision.

The final model request contains exactly those two messages and a JSON schema.
It has no tools and requests only:

```json
{
  "energyplus_zone_name": "SPACE1-1",
  "proposed_setpoint_c": 22.5,
  "objective": "reduce_peak_demand",
  "confidence": 0.65,
  "reason": "A conservative adjustment may reduce cooling demand while preserving comfort."
}
```

Python adds identifiers, timestamps, classifications, evidence references, and
other deterministic metadata. Hidden chain-of-thought is neither requested nor
stored.

### Latency and timeout management

The live demonstration disables Qwen thinking and limits request time, total
agent time, tool rounds, retries, context, and generated tokens. Initial
readiness, MCP execution, final generation, validation, and total duration are
recorded separately. Local latency remains dependent on CPU, memory, model
warmth, and thermal conditions.

On timeout, the UI stops progress, returns a typed
`AGENT_RUN_TIMEOUT` result, and states that no action was applied. An advisory
fallback remains explicit rather than being relabeled as model output.

## 5. Asynchronous and non-blocking control design

Ollama and MCP work is orchestrated asynchronously outside EnergyPlus runtime
callbacks. The callback path consumes a prevalidated candidate or a
deterministic policy decision and performs only bounded telemetry, rule, handle,
and actuator operations. This avoids pausing EnergyPlus physics for
hardware-dependent inference.

The Streamlit app likewise starts expensive operations only from explicit
buttons. Page imports and navigation do not call Ollama or execute EnergyPlus.

## 6. Typed advisory proposal

Pydantic schemas constrain zone name, setpoint, objective, confidence, reason,
classification, and validation results. The final proposal is rejected when it
is malformed, incomplete, unsupported by official evidence, or outside the
advisory contract. Retries are bounded and the live UI permits only one retry.

Advisory output is not described as an applied action, an optimized result, or
a savings result.

## 7. Deterministic validation

Python validates:

- exact zone identity and supported actuator target;
- numeric ranges and cooling/heating deadband;
- evidence classification and completeness;
- context freshness and required telemetry;
- objective and confidence shape;
- prompt-injection-resistant tool boundaries;
- advisory-only execution flags.

Only a typed, valid candidate proceeds to Phase 9.

## 8. Safety supervisor

The supervisor evaluates occupied temperature or the declared proxy, demand
guardrails, telemetry freshness, maximum change, rate limits, oscillation,
actuator state, and recovery conditions. It can produce:

- approve;
- clamp;
- hold;
- reject;
- rollback;
- emergency fallback.

Twenty-two of twenty-two fault scenarios pass, all outcomes are exercised, and
the accepted safety runs contain zero severe and zero fatal errors. Demand
thresholds are prototype project guardrails and require site commissioning.

## 9. Actuator discovery and runtime callback design

The runtime layer discovers exact Data Transfer API handles rather than relying
on a guessed numeric handle. The verified identifier is:

```text
Zone Temperature Control | Cooling Setpoint | SPACE1-1
```

Callbacks are registered at deterministic simulation points. They:

1. wait until API data is ready;
2. resolve and cache handles;
3. capture current telemetry;
4. request a bounded safety decision;
5. write only an approved setpoint;
6. observe the later actuator value;
7. record action, decision, and verification identifiers;
8. reset the actuator to baseline control when required.

Callback exceptions are captured as runtime evidence and fail the acceptance
gate; they are not silently suppressed.

## 10. Rollback and fallback

The fixed Phase 5 schedule is the safe default. Missing/stale telemetry, unsafe
comfort or demand state, oscillation, actuator mismatch, provider failure, or
explicit recovery rules prevent or reverse control. Fallback restores the
baseline behavior. Rollback and emergency recovery have separately classified
events and acceptance checks.

## 11. Evidence and artifact classification

Major evidence classes include:

- development-only simulation and baseline;
- official EnergyPlus baseline;
- verified local MCP audit;
- LLM advisory proposal;
- official EnergyPlus safety-supervised controlled evaluation;
- deterministic safety validation;
- official EnergyPlus quantitative comparison;
- reproducibility report;
- submission document and manifest.

Classifications, run IDs, source, success, hashes, and relationships are
persisted. The UI displays project-relative paths and only offers downloads from
approved repository evidence roots.

## 12. Comparison compatibility gate

Phase 10 refuses a savings claim unless required checks pass for:

- EnergyPlus backend, source, version, and success;
- accepted baseline and controlled classifications;
- base and derived model relationship;
- weather, run period, and reporting frequency;
- occupancy, internal loads, and zone mapping;
- complete expected intervals and critical telemetry;
- severe/fatal error policy;
- verified control injection and enabled safety authority.

After compatibility, 8,760 facility intervals and 52,560 zone records are
aligned. Metrics are computed from full-resolution artifacts; chart
downsampling affects display only.

## 13. Log and error handling

MCP calls, agent runs, control actions, safety decisions, callback errors,
fallbacks, rollbacks, EnergyPlus warnings, manifests, telemetry, and comparison
checks have dedicated artifacts. User-facing errors explain the affected
feature and safe next step; technical diagnostics remain in expanders.
Audit evidence is never deleted by cleanup.

Generated runtime artifacts may contain machine-local provenance paths required
for reproducibility. Dashboard paths and documentation are repository-relative,
and `.env` plus local logs/caches are ignored.

## 14. Reproducibility

The reproducibility verifier runs the controlled annual policy again and builds
a second compatible comparison. It requires matching model/weather hashes,
telemetry shape, action counts, comparison status, and energy/peak/comfort
metrics within `1e-6`. The dashboard declares reproducibility only when the
displayed comparison ID is exactly the second ID in the passing report.

The preserved verified result is:

- baseline facility electricity: `58,568.21190808615 kWh`;
- controlled facility electricity: `58,562.58583227383 kWh`;
- difference: `5.626075812324416 kWh` (`0.009606022839067856%`);
- occupied-temperature proxy change: `+0.16718913270637614` percentage points;
- peak-demand change: effectively unchanged;
- severe/fatal errors: `0 / 0`.

## 15. Technical scope and assumptions

- One zone is controlled conservatively in a retained example model.
- PMV/PPD is genuinely unavailable; no PMV value is fabricated.
- Cost uses an INR 8/kWh project assumption.
- Carbon uses a 708 g CO₂/kWh project assumption.
- The local LLM is advisory and hardware-dependent.
- The final annual comparison uses a deterministic reproducible policy.
- The measured facility-level effect is small and peak demand is unchanged.
- Multi-zone coordination, native-PMV validation, site-calibrated thresholds,
  real tariffs, and a read-only building shadow deployment remain future work.

## 16. Presentation architecture

The Phase 11 interface is a read-only presentation layer over the accepted
Phase 1–10 modules and artifacts. A single local stylesheet supplies warm ivory,
near-black, thin-border, and semantic-status tokens. Home, Architecture, and
Demo Flow are judge-facing narrative pages; Phase 1–9 keep their working
renderers inside the Developer Mode technical expander; Phase 10 reads only the
newest valid reproducible bundle.

Judge Mode is the default and disables accidental access to expensive execution
controls while preserving classifications, scope disclosures, artifact paths,
and downloads. Developer Mode exposes the original explicit run controls and
diagnostics. No navigation or page import starts EnergyPlus, Ollama, MCP client
execution, Phase 9, or Phase 10.

The presentation uses only local assets:

- `assets/logo_mark.svg`
- `assets/architecture_flow.svg`
- `assets/closed_loop_flow.svg`
- `assets/result_summary.svg`

Chart sampling is display-only, retains the exact final row, and never feeds a
metric calculation.

## 17. Phase 12 product architecture

Phase 12 adds a product-centric shell over the same accepted artifacts and
renderers. Command Center, AI Copilot, Building, Analytics, Decisions, Safety,
EnergyPlus, and Reports are the primary routes. The old Phase 1–11 routes stay
registered and become visible in Developer Mode. Guided Demo is a registered
seven-scene replay route opened from Command Center.

Verified Demo Replay is the default and performs no automatic service work.
Live Copilot questions explicitly reuse the Phase 7 Ollama client, MCP bridge,
and advisory agent. A live control proposal is also evaluated by the existing
Phase 9 supervisor against a saved EnergyPlus telemetry state, but the UI has
no actuator write boundary. EnergyPlus execution remains limited to the
preserved explicit developer workflows.

Immutable artifact reads are cached by path, modification time, and size.
Annual telemetry is column-selected and downsampled only for visualization;
official metrics always come from the full-resolution Phase 10 summary.
