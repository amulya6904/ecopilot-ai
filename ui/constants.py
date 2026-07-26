"""Presentation-only constants for the Phase 11 submission experience."""

from dataclasses import dataclass


PROJECT_TITLE = "EcoPilot AI"
PROJECT_SUBTITLE = (
    "Safety-Supervised Autonomous EnergyPlus Building Control"
)
PROJECT_STATEMENT = (
    "EcoPilot AI combines EnergyPlus, a local open-source LLM, MCP tools, "
    "deterministic safety supervision, and runtime actuator control to "
    "demonstrate an auditable closed-loop smart-building proof of concept."
)
HONEST_RESULT_CLAIM = (
    "Under a fully aligned and reproducible EnergyPlus experiment, the "
    "safety-supervised one-zone control policy reduced annual facility "
    "electricity by approximately 5.626 kWh, or 0.0096%. "
    "Occupied-temperature proxy compliance improved slightly relative to "
    "the fixed-schedule baseline, while peak demand remained effectively "
    "unchanged."
)
SMALL_RESULT_NOTE = (
    "The measured whole-building effect is small because this proof of "
    "concept controls one zone conservatively under strict safety constraints."
)
COMFORT_WORDING = (
    "Configured occupied-temperature proxy did not degrade relative to "
    "baseline."
)


@dataclass(frozen=True)
class PhasePageSpec:
    """Judge-facing metadata wrapped around an existing phase renderer."""

    key: str
    title: str
    objective: str
    classification: str
    status: str
    verified: tuple[str, ...]
    not_claimed: str
    primary_controls: str
    evidence: str
    artifacts: tuple[str, ...]
    next_step: str
    judge_priority: bool = False


PHASE_SPECS = {
    "phase1": PhasePageSpec(
        "phase1",
        "Phase 1 — Configuration",
        "Freeze validated building, comfort, simulation, and control schemas.",
        "Configuration foundation",
        "Complete",
        (
            "Typed settings and shared schemas",
            "Zone inventory and deterministic defaults",
        ),
        "No official simulation or savings result.",
        "Inspect frozen configuration and architecture boundaries.",
        "Configuration modules and schema tests.",
        ("config/", "schemas/", "tests/test_settings.py"),
        "Use the lightweight simulator to validate the interface.",
    ),
    "phase2": PhasePageSpec(
        "phase2",
        "Phase 2 — Lightweight simulator",
        "Validate telemetry and UI flow with a seeded development simulator.",
        "Development only",
        "Complete",
        (
            "Three-zone seeded simulator",
            "Weather, occupancy, IAQ, temperature, and energy telemetry",
        ),
        "Not official EnergyPlus evidence and not used for savings.",
        "Run an explicit development scenario; nothing runs on page load.",
        "Seeded simulator output and development-only CSV.",
        ("simulator/", "results/development/"),
        "Compare a fixed development schedule in Phase 3.",
    ),
    "phase3": PhasePageSpec(
        "phase3",
        "Phase 3 — Development baseline",
        "Exercise a conventional fixed schedule on the development simulator.",
        "Development only",
        "Complete",
        (
            "Repeatable fixed-schedule controller",
            "Development energy, cost, carbon, and comfort metrics",
        ),
        "Not the official baseline and never promoted into Phase 10.",
        "Run a seeded baseline scenario and export its development CSV.",
        "Development controller outputs and regression tests.",
        ("controllers/", "results/development/"),
        "Move to the official EnergyPlus pipeline in Phase 4.",
    ),
    "phase4": PhasePageSpec(
        "phase4",
        "Phase 4 — EnergyPlus integration",
        "Verify real EnergyPlus execution, telemetry, diagnostics, and units.",
        "Official EnergyPlus",
        "Complete",
        (
            "EnergyPlus 26.1 execution",
            "Facility and zone telemetry separation",
        ),
        "No AI control, optimization, or savings comparison.",
        "Inspect readiness or explicitly launch a batch validation.",
        "EnergyPlus output, metadata, and diagnostic records.",
        ("energyplus/output/official/", "energyplus/metadata/"),
        "Freeze the official fixed-schedule baseline in Phase 5.",
    ),
    "phase5": PhasePageSpec(
        "phase5",
        "Phase 5 — Official EnergyPlus baseline",
        "Create the manifest-frozen fixed-schedule annual reference run.",
        "Official EnergyPlus",
        "Complete",
        (
            "8,760 facility and 52,560 zone records",
            "Reproducible model, weather, schedules, and telemetry",
        ),
        "A baseline alone is not a savings result.",
        "Inspect persisted evidence or explicitly rerun EnergyPlus.",
        "Manifest, summary, telemetry, hashes, and diagnostics.",
        ("results/official/", "energyplus/models/baseline/"),
        "Expose bounded official evidence through MCP in Phase 6.",
    ),
    "phase6": PhasePageSpec(
        "phase6",
        "Phase 6 — MCP tool layer",
        "Expose bounded official EnergyPlus evidence through local MCP tools.",
        "Verified local MCP",
        "Complete",
        (
            "16 tools and 6 resources",
            "Local stdio, bounded output, path controls, and audit logging",
        ),
        "The MCP layer has no direct actuator authority.",
        "Inspect the catalogue or run the explicit client smoke test.",
        "Tool catalogue, resources, and append-only audit.",
        ("mcp_service/", "results/audit/mcp_tool_calls.jsonl"),
        "Use the read-only evidence in the Phase 7 advisory agent.",
    ),
    "phase7": PhasePageSpec(
        "phase7",
        "Phase 7 — Open-source LLM agent",
        "Generate a typed, evidence-grounded advisory with local qwen3:4b.",
        "Advisory only",
        "Complete",
        (
            "Local Ollama/qwen3:4b structured advisory",
            "MCP evidence plan, bounded output, timeout, and fallback",
        ),
        "The LLM never writes an actuator and latency is hardware dependent.",
        "Optionally run one advisory; no model call occurs on import.",
        "Agent audit, tool history, validated proposal, and latency fields.",
        ("results/agent/phase7/", "results/audit/agent_runs.jsonl"),
        "Convert a safe candidate through the Phase 8 runtime path.",
    ),
    "phase8": PhasePageSpec(
        "phase8",
        "Phase 8 — Closed-loop runtime control",
        "Verify the real Runtime API actuator, observation, reset, and fallback.",
        "Safety supervised",
        "Complete",
        (
            "One verified cooling-setpoint actuator path",
            "Control injection, observed change, reset, and fallback",
        ),
        "Runtime validation is not an optimization or savings result.",
        "Inspect pre-generated evidence or launch an explicit validation.",
        "Handle registry, telemetry, applied actions, and summaries.",
        ("results/closed_loop/phase8/", "energyplus/output/official/phase8/"),
        "Place deterministic final authority in Phase 9.",
    ),
    "phase9": PhasePageSpec(
        "phase9",
        "Phase 9 — Safety supervisor",
        "Apply deterministic comfort, demand, freshness, and recovery rules.",
        "Safety supervised",
        "Complete",
        (
            "22/22 fault scenarios and all six decision outcomes",
            "Post-action verification, rollback, and emergency fallback",
        ),
        "Prototype thresholds are not production safety certification.",
        "Inspect accepted evidence or explicitly run safety validation.",
        "Safety decisions, rule results, fault suite, and recovery events.",
        ("results/safety/phase9/", "results/audit/phase9_safety_events.jsonl"),
        "Measure the complete compatible experiment in Phase 10.",
    ),
    "phase10": PhasePageSpec(
        "phase10",
        "Phase 10 — Quantitative results",
        "Compare compatible annual baseline and controlled EnergyPlus runs.",
        "Official EnergyPlus",
        "Complete",
        (
            "Compatibility and 100% telemetry alignment",
            "Reproducible claim-gated energy, demand, and comfort result",
        ),
        "No meaningful peak reduction, multi-zone result, or deployment claim.",
        "Review the persisted measured result; no simulation runs on page load.",
        "Comparison manifest, aligned telemetry, charts, and reproducibility.",
        ("results/comparison/phase10/",),
        "Use the evidence package for the final submission.",
        judge_priority=True,
    ),
}


__all__ = [
    "COMFORT_WORDING",
    "HONEST_RESULT_CLAIM",
    "PHASE_SPECS",
    "PROJECT_STATEMENT",
    "PROJECT_SUBTITLE",
    "PROJECT_TITLE",
    "SMALL_RESULT_NOTE",
    "PhasePageSpec",
]
