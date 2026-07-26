from safety.demand import evaluate_demand
from safety.fault_injection import make_candidate, make_state


def test_demand_classifies_normal_warning_critical_and_unavailable():
    assert evaluate_demand(make_state(), make_candidate()).status == "normal"
    assert (
        evaluate_demand(
            make_state(facility_demand_kw=24.0), make_candidate()
        ).status
        == "warning"
    )
    assert (
        evaluate_demand(
            make_state(facility_demand_kw=30.0), make_candidate()
        ).status
        == "critical"
    )
    assert (
        evaluate_demand(
            make_state(facility_demand_kw=None), make_candidate()
        ).status
        == "unavailable"
    )


def test_elevated_demand_rejects_demand_increasing_direction():
    result = evaluate_demand(
        make_state(facility_demand_kw=30.0),
        make_candidate(requested=21.0),
    )
    assert any(
        item.rule_id == "DEMAND_INCREASING_ACTION_REJECTED"
        and not item.passed
        for item in result.rules
    )
