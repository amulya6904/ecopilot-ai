"""Exact Data Transfer API identifiers requested before each Phase 8 run."""

from dataclasses import dataclass
from typing import Any

from .settings import PHASE8_SETTINGS, Phase8Settings


@dataclass(frozen=True)
class ExchangeIdentifier:
    field: str
    exchange_type: str
    name: str
    key: str
    required: bool


def required_exchange_identifiers(
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> tuple[ExchangeIdentifier, ...]:
    zone = settings.controlled_zone
    return (
        ExchangeIdentifier(
            "zone_temperature", "variable",
            "Zone Mean Air Temperature", zone, True,
        ),
        ExchangeIdentifier(
            "outdoor_temperature", "variable",
            "Site Outdoor Air Drybulb Temperature", "Environment", True,
        ),
        ExchangeIdentifier(
            "cooling_setpoint", "variable",
            "Zone Thermostat Cooling Setpoint Temperature", zone, True,
        ),
        ExchangeIdentifier(
            "heating_setpoint", "variable",
            "Zone Thermostat Heating Setpoint Temperature", zone, False,
        ),
        ExchangeIdentifier(
            "occupancy", "variable",
            "Zone People Occupant Count", zone, False,
        ),
        ExchangeIdentifier(
            "facility_demand", "variable",
            "Facility Total Electricity Demand Rate", "Whole Building", False,
        ),
        ExchangeIdentifier(
            "facility_energy", "meter",
            "Electricity:Facility", "", False,
        ),
        ExchangeIdentifier(
            "relative_humidity", "variable",
            "Zone Air Relative Humidity", zone, False,
        ),
        ExchangeIdentifier(
            "pmv", "variable",
            "Zone Thermal Comfort Fanger Model PMV",
            f"{zone} People 1", False,
        ),
        ExchangeIdentifier(
            "ppd", "variable",
            "Zone Thermal Comfort Fanger Model PPD",
            f"{zone} People 1", False,
        ),
    )


def request_runtime_variables(
    exchange: Any,
    state: Any,
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> None:
    """Request output variables before EnergyPlus begins its run."""
    for identifier in required_exchange_identifiers(settings):
        if identifier.exchange_type == "variable":
            exchange.request_variable(state, identifier.name, identifier.key)


__all__ = [
    "ExchangeIdentifier",
    "request_runtime_variables",
    "required_exchange_identifiers",
]
