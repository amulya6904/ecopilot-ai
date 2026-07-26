from pathlib import Path

import pandas as pd

from energyplus.baseline.settings import EnergyPlusBaselineSettings
from energyplus.adapter.discovery import EnergyPlusAvailability
from energyplus.adapter.runner import EnergyPlusRunResult
from energyplus.baseline.manifest import calculate_sha256
from energyplus.baseline.metrics import BaselineMetrics
from energyplus.baseline.model_builder import BaselineModelBuildResult
from energyplus.baseline.normalizer import NormalizedBaselineTelemetry
import energyplus.baseline.runner as runner


def _settings(tmp_path: Path) -> EnergyPlusBaselineSettings:
    source = tmp_path / "energyplus/models/modified/source.idf"
    weather = tmp_path / "energyplus/weather/weather.epw"
    source.parent.mkdir(parents=True)
    weather.parent.mkdir(parents=True)
    source.write_text("Version,26.1;", encoding="utf-8")
    weather.write_text("weather", encoding="utf-8")
    return EnergyPlusBaselineSettings(
        repository_root=tmp_path,
        base_model_path=source,
        baseline_model_path=Path("energyplus/models/baseline/baseline.idf"),
        weather_file_path=weather,
        official_output_root=Path("energyplus/output/official/baseline"),
        official_results_root=Path("results/official"),
        metadata_root=Path("energyplus/metadata/baseline"),
    )


def _availability(settings, *, ready: bool = True):
    return EnergyPlusAvailability(
        installed=ready,
        available=ready,
        ready_for_run=ready,
        executable_found=ready,
        executable_path=Path("energyplus.exe") if ready else None,
        installation_dir=Path(".") if ready else None,
        idd_path=Path("Energy+.idd") if ready else None,
        idd_found=ready,
        detected_version="26.1.0" if ready else None,
        expected_version="26.1",
        version_compatible=True if ready else None,
        model_exists=True,
        weather_exists=True,
        output_root_ready=True,
        reason=None if ready else "not ready",
        readiness_issues=() if ready else ("EnergyPlus executable was not found.",),
    )


def _build(settings, *, success: bool = True):
    source = settings.resolve(settings.base_model_path)
    destination = settings.resolve(settings.baseline_model_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if success:
        destination.write_text("Version,26.1;", encoding="utf-8")
    return BaselineModelBuildResult(
        success=success,
        source_model_path=source,
        destination_model_path=destination,
        source_model_hash=calculate_sha256(source),
        destination_model_hash=(
            calculate_sha256(destination) if success else None
        ),
        schedules_inspected=1,
        schedules_modified=("Cooling",),
        output_requests_added=("Electricity:Facility",),
        warnings=(),
        assumptions=(),
        failure_reason=None if success else "build broke",
        inspection_metadata_path=None,
        inspection=None,
    )


def _energyplus_run(settings, *, success: bool = True, fatal: int = 0):
    output = settings.resolve(settings.official_output_root) / "mock-run"
    output.mkdir(parents=True, exist_ok=True)
    csv = output / "eplusout.csv"
    csv.write_text("Date/Time\n", encoding="utf-8")
    stdout = output / "stdout.log"
    stderr = output / "stderr.log"
    metadata = output / "metadata.json"
    stdout.write_text("", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    metadata.write_text("{}", encoding="utf-8")
    return EnergyPlusRunResult(
        run_id="mock-run",
        success=success,
        exit_code=0 if success else 1,
        timed_out=False,
        duration_seconds=1,
        output_dir=output,
        error_file_path=None,
        eso_output_path=output / "eplusout.eso",
        csv_output_path=csv,
        sql_output_path=None,
        stdout_log_path=stdout,
        stderr_log_path=stderr,
        metadata_path=metadata,
        warning_count=0,
        severe_count=0,
        fatal_count=fatal,
        failure_reason=None if success else "fatal",
        official_result=success,
    )


def _normalized(required: bool = True):
    zone = pd.DataFrame({
        "timestamp": pd.to_datetime(["2000-01-01 10:00"]),
        "energyplus_zone_name": ["SPACE1-1"],
        "display_zone_name": ["Open Office"],
        "zone_role": ["primary_occupied"],
        "indoor_temperature_c": [23.0],
        "cooling_setpoint_c": [22.0],
    })
    facility = pd.DataFrame({
        "timestamp": pd.to_datetime(["2000-01-01 10:00"]),
        "facility_electricity_kwh": [1.0],
        "facility_demand_kw": [1.0],
    })
    return NormalizedBaselineTelemetry(
        zone=zone,
        facility=facility,
        actual_available_outputs={
            "zone_temperature": required,
            "facility_electricity": required,
            "facility_demand": required,
            "outdoor_temperature": required,
            "cooling_setpoint": required,
        },
        source_columns=("Date/Time",),
    )


def _metrics():
    return BaselineMetrics(
        summary={
            "total_facility_electricity_kwh": 1.0,
            "total_hvac_electricity_kwh": None,
            "average_facility_demand_kw": 1.0,
            "peak_facility_demand_kw": 1.0,
            "peak_demand_timestamp": "2000-01-01T10:00:00",
            "temperature_compliance_percent": 100.0,
            "pmv_available": False,
            "pmv_compliance_percent": None,
            "thermostat_adherence_percent": 100.0,
            "occupancy_available": False,
            "occupancy_source": "schedule_proxy",
        },
        zone_summary=pd.DataFrame({"energyplus_zone_name": ["SPACE1-1"]}),
        schedule_boundary_table=pd.DataFrame({"matches": [True]}),
    )


def _patch_success(monkeypatch, settings, *, required: bool = True):
    build = _build(settings)
    called = {"phase4_runner": False}
    monkeypatch.setattr(runner, "discover_energyplus", lambda _: _availability(settings))
    monkeypatch.setattr(
        runner, "build_phase5_baseline_model", lambda *_: build
    )
    def fake_run(*args, **kwargs):
        called["phase4_runner"] = True
        return _energyplus_run(settings)
    monkeypatch.setattr(runner, "run_energyplus", fake_run)
    monkeypatch.setattr(
        runner, "normalize_energyplus_baseline_csv",
        lambda *_: _normalized(required),
    )
    monkeypatch.setattr(runner, "calculate_baseline_metrics", lambda *_: _metrics())
    monkeypatch.setattr(
        runner, "inspect_baseline_model",
        lambda *_: type("Inspection", (), {
            "run_periods": (), "timesteps": (), "occupancy_references": (),
            "people_objects": (), "lights_objects": (),
            "electric_equipment_objects": (),
            "hvac_availability_schedules": (),
        })(),
    )
    return called


def test_success_uses_phase4_runner_and_writes_official_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    called = _patch_success(monkeypatch, settings)
    result = runner.run_energyplus_baseline(settings, run_id="test-run")
    assert result.success, result.failure_reason
    assert called["phase4_runner"]
    assert result.classification == "official_energyplus_baseline"
    assert result.official_result and result.baseline_result
    assert not result.ai_controlled
    assert not result.closed_loop
    assert not result.optimized
    assert not result.savings_result
    assert result.manifest_path and result.manifest_path.is_file()
    assert result.artifact_paths["summary"].is_file()
    assert result.model_build_result.source_model_path != (
        result.model_build_result.destination_model_path
    )


def test_unavailable_energyplus_fails_without_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        runner, "discover_energyplus", lambda _: _availability(settings, ready=False)
    )
    result = runner.run_energyplus_baseline(settings)
    assert not result.success
    assert result.backend_id == "energyplus"
    assert "not ready" in (result.failure_reason or "")


def test_model_build_failure_is_propagated(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(runner, "discover_energyplus", lambda _: _availability(settings))
    monkeypatch.setattr(
        runner, "build_phase5_baseline_model",
        lambda *_: _build(settings, success=False),
    )
    result = runner.run_energyplus_baseline(settings)
    assert not result.success
    assert "build broke" in (result.failure_reason or "")


def test_missing_required_telemetry_fails(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    _patch_success(monkeypatch, settings, required=False)
    result = runner.run_energyplus_baseline(settings)
    assert not result.success
    assert "Missing required Phase 5 telemetry" in (result.failure_reason or "")
    assert not (settings.resolve(settings.official_results_root) / "phase5_energyplus_baseline_summary.json").exists()


def test_energyplus_fatal_failure_is_not_classified_official(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(runner, "discover_energyplus", lambda _: _availability(settings))
    monkeypatch.setattr(
        runner, "build_phase5_baseline_model", lambda *_: _build(settings)
    )
    monkeypatch.setattr(
        runner,
        "run_energyplus",
        lambda *_args, **_kwargs: _energyplus_run(
            settings, success=False, fatal=1
        ),
    )
    result = runner.run_energyplus_baseline(settings)
    assert not result.success
    assert not result.official_result
    assert result.energyplus_run_result.fatal_count == 1
