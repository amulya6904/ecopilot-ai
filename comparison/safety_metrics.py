"""Aggregate deterministic Phase 9 intervention and recovery evidence."""

from typing import Any

from .schemas import SafetyMetrics


def _rule_action_count(
    rules: list[dict[str, Any]], predicate
) -> int:
    action_keys: set[str] = set()
    for index, item in enumerate(rules):
        if item.get("passed", True):
            continue
        if not predicate(str(item.get("rule_id", ""))):
            continue
        action_keys.add(
            str(
                item.get("action_id")
                or item.get("decision_id")
                or f"rule-{index}"
            )
        )
    return len(action_keys)


def calculate_safety_metrics(
    *,
    decisions: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    rollbacks: list[dict[str, Any]],
    emergencies: list[dict[str, Any]],
) -> SafetyMetrics:
    interventions = sum(
        item.get("decision") != "approve" for item in decisions
    )
    prevented = sum(
        item.get("decision")
        in {
            "approve_with_clamp",
            "hold",
            "reject",
            "fallback",
            "emergency_fallback",
        }
        for item in decisions
    )
    rollback_successes = sum(
        bool(item.get("reset_succeeded")) for item in rollbacks
    )
    emergency_successes = sum(
        bool(item.get("baseline_restored")) for item in emergencies
    )
    return SafetyMetrics(
        intervention_rate=(
            float(interventions / len(decisions)) if decisions else 0.0
        ),
        unsafe_actions_prevented=prevented,
        comfort_risk_actions_prevented=_rule_action_count(
            rules,
            lambda code: (
                not code.startswith("PMV_UNAVAILABLE")
                and (
                    "COMFORT" in code
                    or "PMV" in code
                    or "TEMPERATURE" in code
                    or "PPD" in code
                )
            ),
        ),
        demand_risk_actions_prevented=_rule_action_count(
            rules, lambda code: code.startswith("DEMAND_")
        ),
        stale_data_rejections=_rule_action_count(
            rules, lambda code: code == "TELEMETRY_STALE"
        ),
        oscillation_detections=_rule_action_count(
            rules, lambda code: code == "ACTION_OSCILLATION_DETECTED"
        ),
        actuator_mismatches=_rule_action_count(
            rules, lambda code: code == "SETPOINT_APPLICATION_MISMATCH"
        ),
        rollback_success_rate=(
            float(rollback_successes / len(rollbacks) * 100)
            if rollbacks
            else None
        ),
        emergency_recovery_success_rate=(
            float(emergency_successes / len(emergencies) * 100)
            if emergencies
            else None
        ),
    )


__all__ = ["calculate_safety_metrics"]
