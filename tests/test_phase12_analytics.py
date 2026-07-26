from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_analytics_renders_required_chart_set_and_filters():
    app = AppTest.from_file("app.py", default_timeout=180).run()
    app.switch_page("app_pages/analytics.py").run(timeout=180)
    assert not app.exception
    assert len(app.get("vega_lite_chart")) >= 12
    labels = {item.label for item in app.selectbox}
    assert {"Zone", "Metric"} <= labels
    toggle_labels = {item.label for item in app.toggle}
    assert {
        "Full-year summary",
        "Occupied only",
        "Action markers",
        "Safety events",
        "Fallback events",
    } <= toggle_labels
    text = Path("ui/demo/analytics.py").read_text(encoding="utf-8")
    for filename in (
        "energy_comparison.csv",
        "demand_comparison.csv",
        "comfort_comparison.csv",
        "action_summary.csv",
        "cost_comparison.csv",
        "carbon_comparison.csv",
    ):
        assert filename in text

