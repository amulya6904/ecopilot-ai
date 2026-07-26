from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_energyplus_status_page_has_only_explicit_workflow_buttons():
    app = AppTest.from_file("app.py", default_timeout=180).run()
    app.switch_page("app_pages/energyplus.py").run(timeout=180)
    assert not app.exception
    assert {
        "Refresh status",
        "Load latest baseline",
        "Load latest controlled run",
        "Run smoke test",
        "Run official baseline",
        "Run runtime validation",
    } <= {button.label for button in app.button}
    source = Path("ui/demo/energyplus_view.py").read_text(encoding="utf-8")
    assert "run_simulation(" not in source
    assert "runtime_runner" not in source

