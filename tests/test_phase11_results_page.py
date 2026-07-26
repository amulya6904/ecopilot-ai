from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.phase10 import RESULT_HEADING, RESULT_NARRATIVE


def test_results_page_renders_executive_claim_and_truthful_metrics():
    app = AppTest.from_file("app.py", default_timeout=90).run()
    app.switch_page("app_pages/phase10.py").run(timeout=120)
    assert not app.exception
    assert [title.value for title in app.title] == [RESULT_HEADING]
    assert "5.626 kWh" in RESULT_NARRATIVE
    assert "0.0096%" in RESULT_NARRATIVE
    assert "peak demand remained effectively unchanged" in RESULT_NARRATIVE
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Verified facility-energy reduction"] == "5.626 kWh"
    assert metrics["Reproducible annual reduction"] == "0.0096%"
    assert metrics["Comfort proxy change"] == "+0.167 pp"
    assert metrics["Measured peak classification"] == "Essentially unchanged"
    assert metrics["PMV"] == "Unavailable"
    assert "Peak demand remained effectively unchanged" in {
        item.value for item in app.subheader
    }


def test_results_page_keeps_small_scope_and_assumptions_visible():
    source = Path("ui/phase10.py").read_text(encoding="utf-8")
    assert "intentionally small" in source
    assert "Genuine PMV/PPD is unavailable" in source
    assert "configured assumptions" in source
    assert "meaningful_action_windows" in source
