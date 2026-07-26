from comparison.safety_metrics import calculate_safety_metrics


def test_safety_intervention_and_recovery_metrics():
    result = calculate_safety_metrics(
        decisions=[
            {"decision": "approve"},
            {"decision": "reject"},
        ],
        rules=[
            {"passed": False, "rule_id": "DEMAND_CRITICAL_ACTIVE"},
            {"passed": False, "rule_id": "TELEMETRY_STALE"},
            {
                "passed": False,
                "rule_id": "PMV_UNAVAILABLE_USING_TEMPERATURE_PROXY",
            },
            {
                "passed": False,
                "rule_id": "TEMPERATURE_PROXY_DIRECTION_RISK",
                "action_id": "unsafe-action",
            },
            {
                "passed": False,
                "rule_id": "TEMPERATURE_PROXY_DIRECTION_RISK",
                "action_id": "unsafe-action",
            },
        ],
        rollbacks=[{"reset_succeeded": True}],
        emergencies=[{"baseline_restored": True}],
    )
    assert result.intervention_rate == 0.5
    assert result.demand_risk_actions_prevented == 1
    assert result.comfort_risk_actions_prevented == 1
    assert result.rollback_success_rate == 100.0
