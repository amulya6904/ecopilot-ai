from safety.fault_injection import run_fault_injection_suite


def test_all_22_fault_scenarios_match_expected_outcomes():
    results = run_fault_injection_suite()
    assert len(results) == 22
    assert all(item["passed"] for item in results)
    assert {item["scenario"] for item in results} >= {
        "Unknown zone",
        "PMV unavailable",
        "Setpoint write mismatch",
        "Severe runtime error",
    }
