import pytest

from comparison.claim_gate import evaluate_claim_gate


def _claim(**updates):
    values = {
        "compatibility_passed": True,
        "controlled_run_complete": True,
        "telemetry_alignment_passed": True,
        "energy_reduction_kwh": 1.0,
        "energy_reduction_percent": 10.0,
        "comfort_gate_passed": True,
        "emergency_comfort_breach": False,
        "severe_count": 0,
        "fatal_count": 0,
        "control_injection_verified": True,
        "safety_supervisor_enabled": True,
    }
    values.update(updates)
    return evaluate_claim_gate(**values)


@pytest.mark.parametrize(
    ("updates", "status"),
    [
        ({}, "validated_positive_savings"),
        ({"comfort_gate_passed": False}, "energy_reduced_comfort_not_maintained"),
        ({"energy_reduction_kwh": 0.0}, "comfort_maintained_no_energy_savings"),
        ({"energy_reduction_kwh": -1.0}, "negative_energy_savings"),
        ({"compatibility_passed": False}, "comparison_invalid"),
        ({"telemetry_alignment_passed": False}, "comparison_incomplete"),
    ],
)
def test_all_claim_gate_outcomes(updates, status):
    result = _claim(**updates)
    assert result.claim_status == status
    assert result.eligible_to_claim_savings is (status == "validated_positive_savings")
