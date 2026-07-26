import pytest

from comparison.artifact_loader import (
    ArtifactLoadError,
    load_baseline_artifact,
    load_controlled_artifact,
)
from tests.phase10_helpers import make_artifact_fixture


def test_valid_phase5_and_controlled_artifacts_load(tmp_path):
    settings, _, controlled = make_artifact_fixture(tmp_path)
    baseline = load_baseline_artifact(settings=settings)
    result = load_controlled_artifact(controlled, settings=settings)
    assert baseline.identity.interval_count == 2
    assert result.identity.control_injection_verified


def test_missing_artifact_is_structured(tmp_path):
    settings, official, _ = make_artifact_fixture(tmp_path)
    (official / "phase5_energyplus_baseline_zone_telemetry.csv").unlink()
    with pytest.raises(ArtifactLoadError) as caught:
        load_baseline_artifact(settings=settings)
    assert caught.value.code == "MISSING_BASELINE_ARTIFACTS"
    assert caught.value.missing
