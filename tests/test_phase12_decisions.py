from streamlit.testing.v1 import AppTest

from ui.demo.decisions import FILTER_OPTIONS


def test_decision_page_preserves_full_lifecycle_filters():
    assert FILTER_OPTIONS == (
        "approved",
        "rejected",
        "corrected",
        "fallback",
        "rollback",
        "timeout",
        "schema failure",
        "actuator failure",
    )
    app = AppTest.from_file("app.py", default_timeout=180).run()
    app.switch_page("app_pages/decisions.py").run(timeout=180)
    assert not app.exception
    subtitles = {item.value for item in app.subheader}
    assert "Applied-action timeline" in subtitles
    assert "Deterministic exception outcomes" in subtitles
    assert app.dataframe

