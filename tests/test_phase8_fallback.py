from datetime import datetime, timezone

from energyplus.runtime_control.fallback import reset_to_baseline


class Exchange:
    def __init__(self): self.reset = []
    def reset_actuator(self, state, handle): self.reset.append(handle)


def test_fallback_uses_reset_actuator():
    exchange = Exchange()
    event = reset_to_baseline(
        exchange, object(), 8, reason_code="VALIDATION_REJECTED",
        simulation_timestamp=datetime.now(timezone.utc),
    )
    assert exchange.reset == [8]
    assert event.actuator_reset
