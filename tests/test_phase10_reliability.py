import pandas as pd

from comparison.reliability import calculate_reliability_metrics


def test_reliability_counts_and_latencies():
    decisions = [
        {"decision": "approve", "duration_ms": 2.0},
        {"decision": "reject", "duration_ms": 4.0},
    ]
    actions = pd.DataFrame([{"observed_setpoint_c": 22.5}])
    result = calculate_reliability_metrics(
        expected_intervals=2,
        completed_intervals=2,
        controlled_summary={"severe_count": 0, "fatal_count": 0},
        actions=actions,
        safety_decisions=decisions,
        safety_summary={"fallbacks": 1, "rollbacks": 0},
    )
    assert result.completion_percent == 100.0
    assert result.proposals == 2
    assert result.average_safety_latency_ms == 3.0
