from energyplus.runtime_control.handles import initialize_handle_registry
from tests.phase8_helpers import ACTUATOR


class Exchange:
    def api_data_fully_ready(self, state): return True
    def get_variable_handle(self, state, name, key):
        return -1 if name == "Zone People Occupant Count" else 2
    def get_meter_handle(self, state, name): return -1
    def get_actuator_handle(self, state, component, control, key): return 7


def test_optional_invalid_handles_do_not_fail_registry():
    registry = initialize_handle_registry(Exchange(), object(), ACTUATOR)
    assert registry.ready
    assert registry.cooling_actuator == 7
    assert "occupancy" in registry.optional_unavailable
    assert registry.exact_identifiers["cooling_actuator"]["actuator_key"] == "SPACE1-1"
