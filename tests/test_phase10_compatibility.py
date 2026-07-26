import pytest

from comparison.compatibility import compare_run_compatibility
from comparison.settings import ComparisonSettings
from tests.phase10_helpers import make_identity


def test_fully_compatible_energyplus_runs(tmp_path):
    report = compare_run_compatibility(
        make_identity(), make_identity("controlled"),
        settings=ComparisonSettings(repository_root=tmp_path),
    )
    assert report.status == "comparable"
    assert all(item.passed for item in report.checks)


@pytest.mark.parametrize(
    ("field", "value", "check_id"),
    [
        ("base_model_hash", "x" * 64, "BASE_MODEL_HASH"),
        ("weather_hash", "y" * 64, "WEATHER_HASH"),
        ("energyplus_version", "25.2", "ENERGYPLUS_VERSION"),
        ("run_period", ["different"], "RUN_PERIOD"),
        ("interval_count", 1, "EXPECTED_INTERVALS"),
        ("critical_telemetry_complete", False, "CRITICAL_TELEMETRY"),
        ("severe_count", 1, "ZERO_SEVERE_ERRORS"),
        ("fatal_count", 1, "ZERO_FATAL_ERRORS"),
    ],
)
def test_required_compatibility_mismatches_fail(
    field, value, check_id, tmp_path
):
    report = compare_run_compatibility(
        make_identity(),
        make_identity("controlled", **{field: value}),
        settings=ComparisonSettings(repository_root=tmp_path),
    )
    assert report.status == "not_comparable"
    assert check_id in report.failed_required_checks
