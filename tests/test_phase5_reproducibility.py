import pandas as pd

from energyplus.baseline.reproducibility import compare_baseline_runs
from energyplus.baseline.runner import EnergyPlusBaselineRunResult


def _result(run_id: str, **changes) -> EnergyPlusBaselineRunResult:
    summary = {
        "base_model_hash": "base",
        "derived_model_hash": "derived",
        "weather_hash": "weather",
        "energyplus_version": "26.1.0",
        "reporting_frequency": "Hourly",
        "total_facility_electricity_kwh": 100.0,
        "peak_facility_demand_kw": 12.0,
        "warning_count": 2,
        "thermostat_adherence_percent": 100.0,
        "temperature_compliance_percent": 90.0,
        "pmv_compliance_percent": None,
    }
    summary.update(changes.pop("summary", {}))
    return EnergyPlusBaselineRunResult(
        run_id=run_id,
        success=changes.pop("success", True),
        official_result=True,
        baseline_result=True,
        baseline_summary=summary,
        facility_telemetry=pd.DataFrame({"x": [1, 2]}),
        zone_telemetry=pd.DataFrame({"x": [1, 2, 3]}),
        **changes,
    )


def test_identical_results_are_reproducible_with_unavailable_pmv() -> None:
    report = compare_baseline_runs(_result("one"), _result("two"), 1e-6)
    assert report.reproducible
    assert report.exact_input_match
    assert report.energy_absolute_difference_kwh == 0
    assert report.telemetry_shape_match
    assert report.warnings_match
    assert not report.mismatches


def test_hash_and_energy_mismatches_are_clear() -> None:
    second = _result(
        "two",
        summary={
            "base_model_hash": "changed",
            "weather_hash": "changed-weather",
            "total_facility_electricity_kwh": 101,
        },
    )
    report = compare_baseline_runs(_result("one"), second, 1e-6)
    assert not report.reproducible
    assert not report.exact_input_match
    assert report.energy_absolute_difference_kwh == 1
    assert any("base_model_hash" in item for item in report.mismatches)
    assert any("weather_hash" in item for item in report.mismatches)
    assert any("Total facility electricity" in item for item in report.mismatches)


def test_telemetry_shape_and_warning_mismatch_detected() -> None:
    second = _result("two", summary={"warning_count": 3})
    second.zone_telemetry = pd.DataFrame({"x": [1]})
    report = compare_baseline_runs(_result("one"), second, 1e-6)
    assert not report.telemetry_shape_match
    assert not report.warnings_match
    assert any("Zone telemetry shape" in item for item in report.mismatches)
