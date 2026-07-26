from energyplus.runtime_control.action_provider import MockActionProvider
from tests.phase8_helpers import ACTUATOR, telemetry


def test_mock_provider_five_interval_plan():
    provider = MockActionProvider()
    decisions = []
    values = [22.0, 22.0, 23.0, 23.0, 22.0]
    for index, value in enumerate(values):
        decision = provider.next_decision(
            telemetry(value, 9 + index), ACTUATOR
        )
        decisions.append(decision)
        if index in {1, 2}:
            provider.observe(23.0, False)
        elif index >= 3:
            provider.observe(22.0, True)
    assert [item.kind for item in decisions] == [
        "apply", "apply", "apply", "reset", "apply"
    ]
    assert decisions[-1].proposal["intentionally_invalid"] is True
    assert provider.intervals_completed == 5
