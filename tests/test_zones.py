"""Tests for building-zone configuration."""

from config.zones import ZONES, validate_zone_configuration


def test_expected_zones() -> None:
    assert len(ZONES) == 3
    assert set(ZONES) == {"office", "conference", "lab"}
    assert {key: value["name"] for key, value in ZONES.items()} == {
        "office": "Open Office", "conference": "Conference Room", "lab": "Computer Lab"
    }


def test_zone_values() -> None:
    for zone in ZONES.values():
        assert zone["area_m2"] > 0
        assert zone["maximum_occupancy"] > 0
        assert zone["maximum_hvac_power_kw"] > 0
        assert 10 <= zone["initial_temperature_c"] <= 40
        assert 0 <= zone["initial_humidity_percent"] <= 100
        assert zone["initial_co2_ppm"] >= 350
        assert zone["equipment_heat_level"] in {"low", "medium", "high"}


def test_zone_validation_completes() -> None:
    validate_zone_configuration()
