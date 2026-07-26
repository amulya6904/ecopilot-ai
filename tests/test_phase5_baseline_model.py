from pathlib import Path
import shutil

from energyplus.baseline.settings import EnergyPlusBaselineSettings
from energyplus.baseline.manifest import calculate_sha256
from energyplus.baseline.model_builder import (
    COOLING_SCHEDULE_NAME,
    HEATING_SCHEDULE_NAME,
    build_phase5_baseline_model,
)


FIXTURE = Path(__file__).parent / "fixtures" / "energyplus" / "phase5_minimal.idf"


def _workspace(tmp_path: Path):
    source = tmp_path / "energyplus/models/modified/source.idf"
    destination = tmp_path / "energyplus/models/baseline/phase5_baseline.idf"
    source.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE, source)
    settings = EnergyPlusBaselineSettings(
        repository_root=tmp_path,
        base_model_path=source,
        baseline_model_path=destination,
        weather_file_path=Path("energyplus/weather/weather.epw"),
        official_output_root=Path("energyplus/output/official/baseline"),
        official_results_root=Path("results/official"),
        metadata_root=Path("energyplus/metadata/baseline"),
    )
    return source, destination, settings


def test_builder_preserves_source_and_derives_model_safely(tmp_path: Path) -> None:
    source, destination, settings = _workspace(tmp_path)
    before = source.read_bytes()
    result = build_phase5_baseline_model(source, destination, settings)
    assert result.success, result.failure_reason
    assert source.read_bytes() == before
    assert result.source_model_hash == calculate_sha256(source)
    assert result.destination_model_hash == calculate_sha256(destination)
    text = destination.read_text(encoding="utf-8")
    assert "EcoPilot AI Phase 5 Official EnergyPlus Baseline" in text
    assert COOLING_SCHEDULE_NAME in text
    assert HEATING_SCHEDULE_NAME in text
    assert f"CoolingSetpoint,\n    {COOLING_SCHEDULE_NAME}" in text
    assert f"HeatingSetpoint,\n    {HEATING_SCHEDULE_NAME}" in text
    assert "SPACE1-1" in text and "PLENUM-1" in text
    assert "BuildingSurface:Detailed" in text
    assert "Zone People Occupant Count" in text
    assert result.inspection_metadata_path
    assert result.inspection_metadata_path.is_file()


def test_required_requests_are_not_duplicated(tmp_path: Path) -> None:
    source, destination, settings = _workspace(tmp_path)
    first = build_phase5_baseline_model(source, destination, settings)
    second = build_phase5_baseline_model(source, destination, settings)
    assert first.success and second.success
    text = destination.read_text(encoding="utf-8").casefold()
    assert text.count("zone mean air temperature") == 1
    assert text.count("zone thermostat cooling setpoint temperature") == 1
    assert first.destination_model_hash == second.destination_model_hash


def test_unsafe_destination_is_rejected(tmp_path: Path) -> None:
    source, _, settings = _workspace(tmp_path)
    result = build_phase5_baseline_model(
        source, tmp_path / "outside.idf", settings
    )
    assert not result.success
    assert "energyplus/models" in (result.failure_reason or "")
