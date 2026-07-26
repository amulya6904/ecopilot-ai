"""Phase 10 agent-evidence metrics for deterministic and LLM-assisted modes."""

from typing import Any

from .schemas import AgentMetrics


def calculate_agent_metrics(
    proposals: list[dict[str, Any]],
    *,
    control_mode: str,
    llm_requests: int = 0,
    valid_structured_outputs: int = 0,
    invalid_structured_outputs: int = 0,
    self_corrections: int = 0,
) -> AgentMetrics:
    decisions = len(proposals)
    confidences = [
        float(item["confidence"])
        for item in proposals
        if isinstance(item.get("confidence"), (int, float))
    ]
    tool_calls = [
        int(item.get("tool_call_count", 0))
        for item in proposals
        if isinstance(item.get("tool_call_count", 0), int)
    ]
    structured_total = valid_structured_outputs + invalid_structured_outputs
    official = sum(
        (
            "EnergyPlusRuntime" in str(item)
            or item.get("source") in {
                "reproducible_policy",
                "phase10_reproducible_policy",
            }
        )
        for item in proposals
    )
    if control_mode == "reproducible_policy":
        official = decisions
    return AgentMetrics(
        average_tool_calls_per_decision=(
            float(sum(tool_calls) / decisions) if decisions else 0.0
        ),
        structured_output_success_rate=(
            float(valid_structured_outputs / structured_total * 100)
            if structured_total
            else None
        ),
        self_corrections=self_corrections,
        average_proposal_confidence=(
            float(sum(confidences) / len(confidences))
            if confidences
            else None
        ),
        decisions_using_official_energyplus_evidence=official,
        total_decisions=decisions,
    )


__all__ = ["calculate_agent_metrics"]
