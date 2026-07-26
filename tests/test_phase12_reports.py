from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ui.demo.data import (
    ArtifactLoadError,
    approved_report_files,
    load_approved_file_bytes,
)


def test_reports_are_project_scoped_and_include_submission_manifest():
    paths = approved_report_files()
    assert any(path.name == "submission_manifest.json" for path in paths)
    assert all(path.is_file() for path in paths)
    with pytest.raises(ArtifactLoadError):
        load_approved_file_bytes(Path("app.py"))


def test_reports_page_renders_all_groups():
    app = AppTest.from_file("app.py", default_timeout=180).run()
    app.switch_page("app_pages/reports.py").run(timeout=180)
    assert not app.exception
    groups = {item.value for item in app.subheader}
    assert {
        "Executive results",
        "Aligned telemetry",
        "Comparison data",
        "Validity and safety",
        "Submission package",
        "Project documentation",
    } <= groups

