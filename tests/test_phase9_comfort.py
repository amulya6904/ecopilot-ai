from safety.comfort import evaluate_comfort
from safety.fault_injection import make_candidate, make_state


def test_temperature_proxy_is_occupancy_aware_and_has_headroom():
    occupied = evaluate_comfort(make_state(pmv=None), make_candidate())
    unoccupied = evaluate_comfort(
        make_state(pmv=None, occupied=False, occupancy_value=0.0),
        make_candidate(),
    )
    assert occupied.comfort_method == "occupied_temperature_proxy"
    assert occupied.safe_headroom_c == 2.0
    assert unoccupied.current_status == "unoccupied"
    assert unoccupied.safe_headroom_c == 7.0


def test_temperature_proxy_rejects_direction_that_worsens_hot_zone():
    result = evaluate_comfort(
        make_state(pmv=None, indoor_temperature_c=26.0),
        make_candidate(requested=23.0),
    )
    assert result.current_status == "too_hot"
    assert any(
        not rule.passed
        and rule.rule_id == "TEMPERATURE_PROXY_DIRECTION_RISK"
        for rule in result.rules
    )
