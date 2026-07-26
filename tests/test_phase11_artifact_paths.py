from pathlib import Path

from ui import artifact_views


def test_download_catalogue_is_project_scoped():
    records = artifact_views.evidence_records()
    assert records
    assert all(artifact_views.is_approved_display_path(item.path) for item in records)
    assert all(
        not Path(item.display_path).is_absolute()
        and item.display_path != "Outside approved project scope"
        for item in records
    )
    assert not artifact_views.is_approved_display_path(
        artifact_views.PROJECT_ROOT.parent / "private.txt"
    )


def test_missing_comparison_directory_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(artifact_views, "PHASE10_ROOT", tmp_path / "missing")
    assert artifact_views.latest_phase10_directory() is None
