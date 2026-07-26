from safety.fault_injection import make_state
from safety.post_action import verify_post_action


def test_safe_post_action_is_verified():
    result = verify_post_action(
        make_state(cooling_setpoint_c=23.0),
        action_id="a",
        approved_value_c=23.0,
        observed_value_c=23.0,
    )
    assert result.verified_safe
    assert result.verified_with_warning
    assert not result.rollback_required


def test_mismatch_comfort_demand_and_actuator_failures_roll_back():
    mismatch = verify_post_action(
        make_state(),
        action_id="a",
        approved_value_c=23.0,
        observed_value_c=22.0,
    )
    assert mismatch.rollback_required
    comfort = verify_post_action(
        make_state(indoor_temperature_c=36.0),
        action_id="b",
        approved_value_c=23.0,
        observed_value_c=23.0,
    )
    assert comfort.emergency_reset_required
    demand = verify_post_action(
        make_state(facility_demand_kw=31.0),
        action_id="c",
        approved_value_c=23.0,
        observed_value_c=23.0,
    )
    assert demand.rollback_required
    actuator = verify_post_action(
        make_state(actuator_valid=False),
        action_id="d",
        approved_value_c=23.0,
        observed_value_c=23.0,
    )
    assert actuator.emergency_reset_required
