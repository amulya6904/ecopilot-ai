"""Tests for central immutable settings."""

from config.settings import AIR_QUALITY, BASELINE, COMFORT, HVAC, OPTIMIZATION, SIMULATION


def test_simulation_timing() -> None:
    assert SIMULATION.total_steps == 144
    assert SIMULATION.step_minutes * SIMULATION.prediction_horizon_steps == 15


def test_comfort_ranges_are_logical() -> None:
    assert COMFORT.occupied_allowed_min_c <= COMFORT.occupied_preferred_min_c
    assert COMFORT.occupied_preferred_max_c <= COMFORT.occupied_allowed_max_c
    assert COMFORT.critical_min_temperature_c <= COMFORT.occupied_allowed_min_c
    assert COMFORT.occupied_allowed_max_c <= COMFORT.critical_max_temperature_c


def test_air_quality_limits_strictly_increase() -> None:
    values = (AIR_QUALITY.outdoor_co2_ppm, AIR_QUALITY.normal_co2_max_ppm,
              AIR_QUALITY.allowed_co2_max_ppm, AIR_QUALITY.warning_co2_max_ppm,
              AIR_QUALITY.critical_co2_max_ppm)
    assert all(left < right for left, right in zip(values, values[1:]))


def test_hvac_candidates_are_inside_limits() -> None:
    assert all(HVAC.minimum_setpoint_c <= value <= HVAC.maximum_setpoint_c
               for value in HVAC.setpoint_candidates_c)
    assert all(HVAC.minimum_fan_speed_percent <= value <= HVAC.maximum_fan_speed_percent
               for value in HVAC.fan_speed_candidates_percent)


def test_baseline_is_valid() -> None:
    BASELINE.validate(HVAC)


def test_optimization_values_are_non_negative() -> None:
    assert all(value >= 0 for name, value in vars(OPTIMIZATION).items()
               if name != "currency_code")
