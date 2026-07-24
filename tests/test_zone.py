"""Tests for a stateful zone simulator."""

from datetime import datetime

import numpy as np

from config.settings import AIR_QUALITY, SIMULATOR_PHYSICS
from config.zones import ZONES
from simulator.models import EnvironmentState, HVACAction, ZoneState
from simulator.zone import ZoneSimulator, comfort_status


def _environment() -> EnvironmentState:
    return EnvironmentState(datetime(2026, 7, 25, 10), 32, 55, 7, 350, 420)


def test_zone_step_bounds_energy_and_reset() -> None:
    zone = ZoneSimulator("office", ZONES["office"], np.random.default_rng(1), 5)
    state = zone.step(datetime(2026, 7, 25, 10), _environment(), 20, HVACAction(24, 50, "medium"))
    assert isinstance(state, ZoneState)
    assert state.cumulative_energy_kwh > 0
    assert state.hvac_power_kw <= ZONES["office"]["maximum_hvac_power_kw"]
    assert SIMULATOR_PHYSICS.minimum_temperature_c <= state.indoor_temperature_c <= SIMULATOR_PHYSICS.maximum_temperature_c
    assert SIMULATOR_PHYSICS.minimum_humidity_percent <= state.humidity_percent <= SIMULATOR_PHYSICS.maximum_humidity_percent
    assert AIR_QUALITY.outdoor_co2_ppm <= state.co2_ppm <= SIMULATOR_PHYSICS.maximum_co2_ppm
    zone.reset()
    assert zone.runtime.temperature_c == ZONES["office"]["initial_temperature_c"]
    assert zone.runtime.cumulative_energy_kwh == 0


def test_comfort_classification() -> None:
    assert comfort_status(23.5, 3) == "Comfortable"
    assert comfort_status(23.5, 0) == "Unoccupied"


def test_lab_equipment_adds_more_heat_than_conference() -> None:
    common = dict(ZONES["conference"])
    common["initial_temperature_c"] = 24.0
    lab_config = dict(common)
    lab_config["equipment_heat_level"] = "high"
    conference_config = dict(common)
    conference_config["equipment_heat_level"] = "low"
    action = HVACAction(24, 50, "medium")
    lab = ZoneSimulator("lab", lab_config, np.random.default_rng(3), 5)
    conference = ZoneSimulator("conference", conference_config, np.random.default_rng(3), 5)
    lab_state = lab.step(_environment().timestamp, _environment(), 0, action)
    conference_state = conference.step(_environment().timestamp, _environment(), 0, action)
    assert lab_state.indoor_temperature_c > conference_state.indoor_temperature_c
