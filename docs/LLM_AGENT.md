# Local LLM, prompt, and latency design

## Role

Phase 7 uses `qwen3:4b` through a local Ollama service. It demonstrates bounded
evidence use and compact structured advice. It does not apply a setpoint,
control EnergyPlus, certify safety, or produce the official Phase 10 savings.

The LLM never has direct actuator authority. Its output must pass Pydantic
parsing, deterministic validation, and the Phase 9 supervisor before it can
even become a runtime candidate.

## Local inference boundary

- Provider: Ollama
- Model: `qwen3:4b`
- Allowed host: loopback only
- Thinking mode: disabled
- Streaming: disabled for the structured request
- Network requirement: none after the model is installed
- Remote providers: unsupported

Run the readiness check without restarting an already listening Ollama service:

```powershell
ollama ps
ollama run qwen3:4b --think=false "Reply with only ready"
python -m scripts.check_ollama
```

## MCP evidence discovery

The agent is permitted to use a fixed allowlist of read-only local MCP tools.
Required official EnergyPlus evidence is retrieved through a deterministic
plan. Each result retains source and classification metadata, and telemetry is
bounded by row and character limits before it enters model context.

This design preserves auditable MCP evidence while avoiding a slow preliminary
tool-selection generation on the live CPU path.

## Prompt structure

The final proposal call contains exactly two messages:

1. a compact system prompt stating role, prohibited claims, allowed semantics,
   output contract, and evidence discipline;
2. a compact user prompt containing only the bounded official evidence needed
   for this decision.

The complete tool-calling conversation is not reused for final generation. The
request provides the Pydantic JSON schema directly and includes no tools:

```python
{
    "model": "qwen3:4b",
    "messages": compact_messages,
    "format": LLMDecision.model_json_schema(),
    "stream": False,
    "think": False,
    "keep_alive": "10m",
    "options": {
        "temperature": 0,
        "num_predict": 192,
        "num_ctx": 4096,
    },
}
```

The model emits only zone, proposed setpoint, objective, confidence, and
reason. Python adds IDs, timestamps, source classification, evidence links, and
validation metadata. Hidden chain-of-thought is not requested, displayed, or
stored.

## Structured schema

The compact output shape is:

```json
{
  "energyplus_zone_name": "SPACE1-1",
  "proposed_setpoint_c": 22.5,
  "objective": "reduce_peak_demand",
  "confidence": 0.65,
  "reason": "A conservative adjustment may reduce cooling demand while preserving comfort."
}
```

Malformed, extra-authority, unsupported, or unsafe output fails deterministic
validation. A model response is never assumed to be trustworthy merely because
it is valid JSON.

## Live latency limits

The existing environment settings define practical CPU-demo limits:

```text
ECOPILOT_LLM_THINK=false
ECOPILOT_LLM_TIMEOUT_SECONDS=180
ECOPILOT_LLM_FINAL_TIMEOUT_SECONDS=180
ECOPILOT_AGENT_RUN_TIMEOUT_SECONDS=360
ECOPILOT_AGENT_MAX_TOOL_ROUNDS=4
ECOPILOT_AGENT_MAX_RETRIES=1
ECOPILOT_LLM_NUM_PREDICT=192
ECOPILOT_LLM_NUM_CTX=4096
```

Latency is divided into:

- Ollama readiness;
- initial tool-selection inference, when that optional mode is used;
- deterministic MCP evidence retrieval;
- final structured generation;
- Python validation;
- total agent duration.

These values are recorded in `run_metadata.json`. The verified local run shows
that final structured generation dominates total latency; exact duration is
hardware-dependent and must not be presented as a universal benchmark.

## Timeout and fallback behavior

Each request has an inner timeout and the complete agent run has an outer
timeout. On outer timeout, the result uses `AGENT_RUN_TIMEOUT` and the UI states:

> The local CPU model did not finish within 6 minutes. No action was applied.

The progress view exits instead of leaving a spinner active. MCP failure,
missing required evidence, schema failure, and validation failure have distinct
typed outcomes. Any deterministic fallback is explicitly labeled as fallback,
not as successful LLM output.

## Why the LLM is outside callbacks

EnergyPlus runtime callbacks must be bounded and deterministic enough to avoid
stalling simulation physics. Local inference can vary with CPU load, memory
pressure, model warmth, and thermal throttling, so the agent runs asynchronously
outside the callback. The callback receives only a prevalidated candidate or a
deterministic policy decision, then performs telemetry, safety, handle, write,
and observation work.

## Why Phase 10 uses a deterministic policy

The final annual comparison must be repeatable and practical on local CPU
hardware. `reproducible_policy` exercises the real actuator, the same Phase 9
safety authority, fallback behavior, telemetry alignment, and EnergyPlus
physics without introducing model-latency nondeterminism into 8,760 hourly
intervals.

Therefore:

- Phase 7 proves local qwen3:4b advisory capability;
- Phases 8–9 prove safe real actuator control;
- Phase 10 measures the deterministic safety-supervised policy;
- no claim is made that qwen3:4b generated the measured savings.

## Scope disclosure

Local inference latency is hardware-dependent. The retained proof of concept
controls one zone and is not a real-building deployment or production safety
certification. Future work includes faster local hardware, multi-zone
coordination, and native PMV evidence while preserving the same trust boundary.
