from dataclasses import replace

import pytest

from comparison.settings import ComparisonSettings


def test_valid_phase10_settings_are_frozen(tmp_path):
    settings = ComparisonSettings(repository_root=tmp_path)
    assert settings.required_backend == "energyplus"
    with pytest.raises(Exception):
        settings.currency = "USD"


@pytest.mark.parametrize(
    "updates",
    [
        {"energy_tolerance_kwh": -1.0},
        {"comfort_tolerance_percent": 101.0},
        {"demand_warning_kw": 31.0, "demand_critical_kw": 30.0},
    ],
)
def test_invalid_phase10_tolerances(updates, tmp_path):
    with pytest.raises(ValueError):
        ComparisonSettings(repository_root=tmp_path, **updates)


def test_invalid_tariff_and_carbon_configuration(tmp_path):
    with pytest.raises(ValueError):
        ComparisonSettings(
            repository_root=tmp_path,
            electricity_tariff_mode="time_of_use",
        )
    with pytest.raises(ValueError):
        ComparisonSettings(
            repository_root=tmp_path,
            carbon_intensity_mode="time_varying",
        )
    assert replace(
        ComparisonSettings(repository_root=tmp_path),
        flat_tariff_per_kwh=1.0,
    ).flat_tariff_per_kwh == 1.0
