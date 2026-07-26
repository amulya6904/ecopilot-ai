from safety.fault_injection import NOW, make_state
from safety.post_action import verify_post_action
from safety.rollback import build_rollback_event, rollback_reason


def test_rollback_records_verified_baseline_restore():
    verification = verify_post_action(
        make_state(),
        action_id="rollback-action",
        approved_value_c=23.0,
        observed_value_c=22.0,
    )
    assert rollback_reason(verification) == "SETPOINT_APPLICATION_MISMATCH"
    event = build_rollback_event(
        verification,
        simulation_timestamp=NOW,
        reset_attempted=True,
        reset_succeeded=True,
        restored_setpoint_c=22.0,
        autonomy_disabled=False,
    )
    assert event.reset_succeeded
    assert event.restored_setpoint_c == 22.0
