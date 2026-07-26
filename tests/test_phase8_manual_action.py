from energyplus.runtime_control.action_provider import ManualActionProvider
from tests.phase8_helpers import ACTUATOR, telemetry


def test_manual_provider_waits_then_requests_23_and_resets():
    provider = ManualActionProvider()
    assert provider.next_decision(telemetry(27.0, 8), ACTUATOR) is None
    apply = provider.next_decision(telemetry(22.0, 9), ACTUATOR)
    assert apply.candidate.requested_value_c == 23.0
    provider.observe(23.0, False)
    reset = provider.next_decision(telemetry(23.0, 10), ACTUATOR)
    assert reset.kind == "reset"
    provider.observe(22.0, True)
    assert provider.complete
