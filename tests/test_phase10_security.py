from pathlib import Path

import pytest

from comparison.artifact_loader import ArtifactLoadError, load_baseline_artifact
from tests.phase10_helpers import make_artifact_fixture


def test_explicit_paths_are_restricted_and_development_is_rejected(tmp_path):
    settings, _, _ = make_artifact_fixture(tmp_path)
    with pytest.raises(ArtifactLoadError) as outside:
        load_baseline_artifact(tmp_path / "outside", settings=settings)
    assert outside.value.code == "PATH_OUTSIDE_RESULTS"
    development = tmp_path / "results" / "development"
    development.mkdir()
    with pytest.raises(ArtifactLoadError) as rejected:
        load_baseline_artifact(development, settings=settings)
    assert rejected.value.code == "DEVELOPMENT_RESULT_REJECTED"


def test_phase10_loader_and_runner_use_no_shell_execution():
    root = Path(__file__).parents[1]
    source = (
        (root / "comparison" / "artifact_loader.py").read_text(encoding="utf-8")
        + (root / "comparison" / "runner.py").read_text(encoding="utf-8")
    )
    assert "shell=True" not in source
    assert "os.system" not in source
