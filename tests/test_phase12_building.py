from streamlit.testing.v1 import AppTest


def test_building_page_identifies_control_scope_and_telemetry():
    app = AppTest.from_file("app.py", default_timeout=180).run()
    app.switch_page("app_pages/building.py").run(timeout=180)
    assert not app.exception
    labels = {metric.label for metric in app.metric}
    assert {
        "Outdoor temperature",
        "Facility demand",
        "Interval electricity",
        "Detected zones",
        "Controlled zones",
        "Latest safe setpoint",
    } <= labels
    text = " ".join(str(item.value) for item in (*app.markdown, *app.caption))
    assert "SPACE1-1" in text
    assert "VERIFIED CONTROL AUTHORITY" in text

