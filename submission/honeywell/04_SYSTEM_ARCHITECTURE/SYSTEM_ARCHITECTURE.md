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

## Required architecture coverage

| Required topic | Primary section |
|---|---|
| System overview | Purpose and verified scope; End-to-end flow |
| Closed-loop architecture | End-to-end flow; Asynchronous and non-blocking control design |
| EnergyPlus integration | EnergyPlus-first design |
| Building-state and telemetry layer | EnergyPlus-first design; MCP communication layer |
| MCP tool-calling architecture | MCP communication layer |
| MCP tool permissions and schemas | MCP tool permissions and schemas |
| `qwen3:4b` / Ollama agent | Local LLM advisory layer |
| Prompt-engineering strategy | Prompt engineering and bounded-context strategy |
| Structured proposal format | Typed advisory proposal |
| Prompt-latency management | Latency and timeout management |
| Long simulation-log handling | Long simulation-log handling and audit logging |
| Deterministic validation | Deterministic validation |
| Safety supervisor | Safety supervisor |
| Runtime actuator injection | Actuator discovery and runtime callback design |
| Rollback and fallback | Rollback and fallback |
| Audit logging | Log and error handling; Long simulation-log handling and audit logging |
| Quantitative-comparison pipeline | Comparison compatibility gate |
| Reproducibility | Reproducibility |
| Official versus development classification | Evidence and artifact classification |
| Technical scope and assumptions | Technical scope and assumptions |

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

## 18. MCP tool permissions and schemas

Every MCP response uses a structured envelope containing `success`,
`tool_name`, `data` or a public `error`, and metadata for source, backend,
classification, timing, record count, truncation, and audit ID. Inputs are
validated, responses are size-bounded, and failures are audited. Read-only
tools never start EnergyPlus or modify controls. The sole execution-class tool,
`run_official_baseline`, can only invoke the existing Phase 5 baseline runner;
it cannot actuate a live control or fall back to the lightweight simulator.

| Tool | Purpose | Input | Output | Permission | Failure mode | Fallback |
|---|---|---|---|---|---|---|
| `get_system_status` | Check project, EnergyPlus, baseline, MCP, SDK, and audit readiness | None | Structured readiness flags and paths | Read-only | Missing dependency or artifact is returned as an unsuccessful envelope | Show readiness issue; apply no action |
| `get_energyplus_readiness` | Check EnergyPlus discovery and configured inputs | None | Installation and input readiness | Read-only | Installation or configured input unavailable | Keep the feature unavailable; do not simulate |
| `get_phase_status` | Report honest implementation status | None | Phase status records | Read-only | Status source unavailable | Display unknown status |
| `get_available_outputs` | Describe official baseline output availability | None | Availability flags and normalized columns | Read-only | Baseline output metadata missing | Treat requested evidence as unavailable |
| `get_official_baseline_summary` | Read the frozen Phase 5 summary | None | Persisted official summary | Read-only | Summary missing or invalid | Stop evidence-dependent advice |
| `get_baseline_manifest` | Read frozen hashes and configuration | None | Sanitized baseline manifest | Read-only | Manifest missing or invalid | Reject official-baseline classification |
| `get_latest_energyplus_run` | Read compact latest-run metadata | None | Run ID, status, counts, and duration | Read-only | No official run found | Report that no run is available |
| `run_official_baseline` | Explicitly execute the existing Phase 5 runner | `verify_reproducibility: bool`, `force_rebuild: bool` | Classified baseline result and counts | Execution; separately gated | Runner, path, timeout, severe, or fatal failure | Return failure; never use the lightweight backend |
| `list_zones` | List technical zones, aliases, roles, and availability | None | Bounded zone records | Read-only | Zone inventory unavailable | Do not invent a zone |
| `get_zone_summary` | Read one official zone summary | `zone_name: str` | Resolved technical name, alias, role, and metrics | Read-only | Unknown or ambiguous zone | Request an exact listed zone |
| `get_zone_telemetry` | Read bounded zone telemetry | `zone_name`, optional `start`, `end`, `aggregation`, `limit` | Filtered records plus truncation metadata | Read-only | Invalid range, aggregation, limit, or missing data | Narrow the range or use a coarser aggregation |
| `get_facility_summary` | Read facility electricity and demand totals | None | Persisted facility metrics | Read-only | Facility summary missing | Make no facility-level claim |
| `get_facility_telemetry` | Read bounded facility telemetry | Optional `start`, `end`, `aggregation`, `limit` | Filtered facility records and truncation metadata | Read-only | Invalid bounds or unavailable telemetry | Narrow or aggregate the query |
| `get_comfort_summary` | Read occupied comfort evidence and PMV availability | None | Proxy/PMV availability and compliance metrics | Read-only | Comfort evidence missing | State that comfort cannot be verified |
| `get_thermostat_adherence` | Read policy-to-output adherence evidence | None | Policy, mismatch count, and bounded samples | Read-only | Setpoint evidence unavailable | Do not assert adherence |
| `get_runtime_errors` | Read bounded EnergyPlus diagnostics | Optional `severity`, `classification`, `limit` | Warning/severe/fatal counters and compact records | Read-only | Invalid filter or diagnostics unavailable | Use run-level counters and surface the limitation |

## 19. Prompt engineering and bounded-context strategy

Telemetry grounding means every model-visible measurement is copied from a
classified MCP result and accompanied by its source and evidence identity.
Structured output is enforced with a JSON schema and then parsed into a typed
proposal. The prompt explicitly forbids fabricated measurements, unsupported
savings claims, and direct actuation. The LLM has advisory authority only;
deterministic Python validation and the safety supervisor retain final
authority.

Context is bounded in three layers: telemetry is summarized into small
decision-relevant records, only limited recent history is retained, and MCP
results have row, character, and byte limits. The final proposal request uses
two compact messages, no tools, a small generation budget, and local
`qwen3:4b` inference. Configured request and overall-agent timeouts terminate
slow inference with an explicit no-action result. Provider failure, malformed
output, or timeout selects a declared fallback. No blocking LLM or MCP call is
made inside an EnergyPlus runtime callback.

## 20. Long simulation-log handling and audit logging

Complete EnergyPlus logs remain with their run output for engineering
diagnosis; they are not copied into model context or this compact submission.
The parser extracts each primary warning, severe error, and fatal error,
preserves a bounded excerpt, classifies warnings, and records separate
severity counters. Repeated warnings remain traceable as individual source
records while classification and counters support aggregation without
repeating full text. User-facing diagnostics use bounded record sets and
concise excerpts or tail-style summaries rather than entire logs.

MCP calls, advisory runs, proposals, validations, safety decisions, actuator
writes, post-action observations, fallbacks, rollbacks, and comparison gates
carry identifiers and timestamps in dedicated audit artifacts. Audit inputs
are sanitized, outputs report truncation and record counts, and internal
exceptions become public structured failures. The LLM sees counters and a
small diagnostic summary only; raw logs remain outside the agent context.
