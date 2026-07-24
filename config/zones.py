"""Frozen building-zone configuration for the Phase 1 prototype."""

from typing import TypedDict


class ZoneConfiguration(TypedDict):
    """Configuration values required for one future simulated zone."""

    name: str
    area_m2: float
    maximum_occupancy: int
    equipment_heat_level: str
    maximum_hvac_power_kw: float
    initial_temperature_c: float
    initial_humidity_percent: float
    initial_co2_ppm: float
    normal_start_hour: int
    normal_end_hour: int


ZONES: dict[str, ZoneConfiguration] = {
    "office": {
        "name": "Open Office", "area_m2": 150.0, "maximum_occupancy": 30,
        "equipment_heat_level": "medium", "maximum_hvac_power_kw": 12.0,
        "initial_temperature_c": 25.0, "initial_humidity_percent": 50.0,
        "initial_co2_ppm": 450.0, "normal_start_hour": 9, "normal_end_hour": 18,
    },
    "conference": {
        "name": "Conference Room", "area_m2": 50.0, "maximum_occupancy": 12,
        "equipment_heat_level": "low", "maximum_hvac_power_kw": 6.0,
        "initial_temperature_c": 25.0, "initial_humidity_percent": 48.0,
        "initial_co2_ppm": 430.0, "normal_start_hour": 9, "normal_end_hour": 18,
    },
    "lab": {
        "name": "Computer Lab", "area_m2": 100.0, "maximum_occupancy": 25,
        "equipment_heat_level": "high", "maximum_hvac_power_kw": 14.0,
        "initial_temperature_c": 26.0, "initial_humidity_percent": 52.0,
        "initial_co2_ppm": 470.0, "normal_start_hour": 9, "normal_end_hour": 18,
    },
}


def validate_zone_configuration(
    zones: dict[str, ZoneConfiguration] | None = None,
) -> None:
    """Raise ``ValueError`` when a zone configuration violates the frozen rules."""
    configured_zones = ZONES if zones is None else zones
    if len(configured_zones) != len(set(configured_zones)):
        raise ValueError("Zone IDs must be unique.")
    for zone_id, zone in configured_zones.items():
        if not zone_id:
            raise ValueError("Zone IDs must not be empty.")
        if not zone["name"].strip():
            raise ValueError(f"{zone_id}: name must not be empty.")
        if zone["area_m2"] <= 0 or zone["maximum_occupancy"] <= 0:
            raise ValueError(f"{zone_id}: area and occupancy must be positive.")
        if zone["maximum_hvac_power_kw"] <= 0:
            raise ValueError(f"{zone_id}: HVAC power must be positive.")
        if not 10 <= zone["initial_temperature_c"] <= 40:
            raise ValueError(f"{zone_id}: temperature must be between 10°C and 40°C.")
        if not 0 <= zone["initial_humidity_percent"] <= 100:
            raise ValueError(f"{zone_id}: humidity must be between 0% and 100%.")
        if zone["initial_co2_ppm"] < 350:
            raise ValueError(f"{zone_id}: CO2 must be at least 350 ppm.")
        if zone["equipment_heat_level"] not in {"low", "medium", "high"}:
            raise ValueError(f"{zone_id}: invalid equipment heat level.")
        start, end = zone["normal_start_hour"], zone["normal_end_hour"]
        if not (0 <= start <= 23 and 0 <= end <= 23 and start < end):
            raise ValueError(f"{zone_id}: operating hours are invalid.")


validate_zone_configuration()
