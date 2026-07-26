"""Post-readiness handle resolution with exact identifier audit data."""

from dataclasses import asdict, dataclass, field
from typing import Any

from .actuator_discovery import ActuatorDescriptor
from .settings import PHASE8_SETTINGS, Phase8Settings
from .variable_discovery import required_exchange_identifiers


@dataclass
class HandleRegistry:
    zone_temperature: int = -1
    outdoor_temperature: int = -1
    cooling_setpoint: int = -1
    heating_setpoint: int = -1
    occupancy: int = -1
    facility_demand: int = -1
    facility_energy: int = -1
    relative_humidity: int = -1
    pmv: int = -1
    ppd: int = -1
    cooling_actuator: int = -1
    initialized: bool = False
    api_ready_when_initialized: bool = False
    exact_identifiers: dict[str, dict[str, Any]] = field(default_factory=dict)
    required_invalid: list[str] = field(default_factory=list)
    optional_unavailable: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.initialized and not self.required_invalid

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"ready": self.ready}


def initialize_handle_registry(
    exchange: Any,
    state: Any,
    actuator: ActuatorDescriptor,
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> HandleRegistry:
    if not exchange.api_data_fully_ready(state):
        raise RuntimeError("EnergyPlus API data is not fully ready.")
    registry = HandleRegistry(api_ready_when_initialized=True)
    for identifier in required_exchange_identifiers(settings):
        if identifier.exchange_type == "meter":
            handle = exchange.get_meter_handle(state, identifier.name)
        else:
            handle = exchange.get_variable_handle(
                state, identifier.name, identifier.key
            )
        setattr(registry, identifier.field, int(handle))
        registry.exact_identifiers[identifier.field] = asdict(identifier)
        if handle == -1:
            target = (
                registry.required_invalid
                if identifier.required
                else registry.optional_unavailable
            )
            target.append(identifier.field)
    registry.cooling_actuator = int(
        exchange.get_actuator_handle(
            state,
            actuator.component_type,
            actuator.control_type,
            actuator.actuator_key,
        )
    )
    registry.exact_identifiers["cooling_actuator"] = {
        "exchange_type": "actuator",
        "component_type": actuator.component_type,
        "control_type": actuator.control_type,
        "actuator_key": actuator.actuator_key,
        "identifier": actuator.identifier,
        "required": True,
    }
    if registry.cooling_actuator == -1:
        registry.required_invalid.append("cooling_actuator")
    registry.initialized = True
    return registry


__all__ = ["HandleRegistry", "initialize_handle_registry"]
