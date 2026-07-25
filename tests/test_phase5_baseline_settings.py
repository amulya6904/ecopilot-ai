from dataclasses import replace
from pathlib import Path

import pytest

from energyplus.baseline.settings import (
    ENERGYPLUS_BASELINE,
    EnergyPlusBaselineSettings,
)


def _settings(tmp_path: Path, **changes) -> EnergyPlusBaselineSettings:
    values = {
        "repository_root": tmp_path,
        "base_model_path": Path("energyplus/models/modified/source.idf"),
        "baseline_model_path": Path("energyplus/models/baseline/baseline.idf"),
        "weather_file_path": Path("energyplus/weather/weather.epw"),
        "official_output_root": Path("energyplus/output/official/baseline"),
        "official_results_root": Path("results/official"),
        "metadata_root": Path("energyplus/metadata/baseline"),
    }
    values.update(changes)
    return EnergyPlusBaselineSettings(**values)


def test_valid_defaults_and_mapping_preserve_technical_names() -> None:
    settings = ENERGYPLUS_BASELINE
    assert settings.occupied_start_hour < settings.occupied_end_hour
    assert settings.occupied_heating_setpoint_c < settings.occupied_cooling_setpoint_c
    assert settings.zone_display_names["SPACE1-1"] == "Open Office"
    assert settings.zone_roles["PLENUM-1"] == "plenum"


@pytest.mark.parametrize(
    "changes",
    (
        {"occupied_start_hour": 18, "occupied_end_hour": 9},
        {"occupied_heating_setpoint_c": 23, "occupied_cooling_setpoint_c": 22},
        {"occupied_temperature_min_c": 25, "occupied_temperature_max_c": 22},
        {"pmv_min": 0.5, "pmv_max": -0.5},
        {"occupied_cooling_setpoint_c": 30},
    ),
)
def test_invalid_baseline_values_are_rejected(
    tmp_path: Path, changes: dict
) -> None:
    with pytest.raises(ValueError):
        _settings(tmp_path, **changes)


def test_source_and_destination_must_differ(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="differ"):
        _settings(
            tmp_path,
            baseline_model_path=Path("energyplus/models/modified/source.idf"),
        )


def test_result_and_model_paths_must_be_repository_safe(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside the repository"):
        _settings(tmp_path, official_results_root=tmp_path.parent / "outside")
    with pytest.raises(ValueError, match="energyplus/models"):
        _settings(tmp_path, baseline_model_path=Path("baseline.idf"))


def test_dataclass_remains_frozen() -> None:
    with pytest.raises(Exception):
        replace(ENERGYPLUS_BASELINE, occupied_start_hour=19, occupied_end_hour=18)
