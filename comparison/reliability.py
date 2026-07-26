"""Controlled-run completion, service, action, and latency metrics."""

from typing import Any

import pandas as pd

from .schemas import ReliabilityMetrics


def _count_decisions(
    decisions: list[dict[str, Any]], value: str
) -> int:
    return sum(item.get("decision") == value for item in decisions)


def _mean(values: list[float]) -> float | None:
    return float(sum(values) / len(values)) if values else None


def calculate_reliability_metrics(
    *,
    expected_intervals: int,
    completed_intervals: int,
    controlled_summary: dict[str, Any],
    actions: pd.DataFrame,
    safety_decisions: list[dict[str, Any]],
    safety_summary: dict[str, Any],
) -> ReliabilityMetrics:
    llm_requests = int(controlled_summary.get("llm_requests", 0))
    llm_responses = int(controlled_summary.get("llm_responses", 0))
    safety_latencies = [
        float(item["duration_ms"])
        for item in safety_decisions
        if isinstance(item.get("duration_ms"), (int, float))
    ]
    verified = (
        int(actions["observed_setpoint_c"].notna().sum())
        if "observed_setpoint_c" in actions
        else 0
    )
    return ReliabilityMetrics(
        expected_intervals=expected_intervals,
        completed_intervals=completed_intervals,
        completion_percent=(
            float(completed_intervals / expected_intervals * 100)
            if expected_intervals
            else 0.0
        ),
        llm_requests=llm_requests,
        llm_responses=llm_responses,
        llm_timeouts=int(controlled_summary.get("llm_timeouts", 0)),
        mcp_calls=int(controlled_summary.get("mcp_calls", 0)),
        mcp_failures=int(controlled_summary.get("mcp_failures", 0)),
        valid_structured_outputs=int(
            controlled_summary.get("valid_structured_outputs", 0)
        ),
        invalid_structured_outputs=int(
            controlled_summary.get("invalid_structured_outputs", 0)
        ),
        proposals=len(safety_decisions),
        approvals=_count_decisions(safety_decisions, "approve"),
        clamps=_count_decisions(
            safety_decisions, "approve_with_clamp"
        ),
        holds=_count_decisions(safety_decisions, "hold"),
        rejections=_count_decisions(safety_decisions, "reject"),
        applied_actions=len(actions),
        verified_actuator_changes=verified,
        fallbacks=max(
            int(safety_summary.get("fallbacks", 0)),
            int(controlled_summary.get("fallback_count", 0)),
        ),
        rollbacks=max(
            int(safety_summary.get("rollbacks", 0)),
            int(controlled_summary.get("rollback_count", 0)),
        ),
        emergency_fallbacks=max(
            int(safety_summary.get("emergency_fallbacks", 0)),
            int(controlled_summary.get("emergency_fallback_count", 0)),
        ),
        severe_count=int(controlled_summary.get("severe_count", 0)),
        fatal_count=int(controlled_summary.get("fatal_count", 0)),
        average_llm_latency_ms=(
            float(controlled_summary["average_llm_latency_ms"])
            if controlled_summary.get("average_llm_latency_ms") is not None
            else None
        ),
        average_mcp_latency_ms=(
            float(controlled_summary["average_mcp_latency_ms"])
            if controlled_summary.get("average_mcp_latency_ms") is not None
            else None
        ),
        average_safety_latency_ms=_mean(safety_latencies),
    )


__all__ = ["calculate_reliability_metrics"]
