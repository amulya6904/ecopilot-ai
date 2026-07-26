from streamlit.testing.v1 import AppTest


def test_command_center_renders_verified_product_summary():
    app = AppTest.from_file("app.py", default_timeout=120).run()
    assert not app.exception
    labels = {metric.label for metric in app.metric}
    assert {
        "Controlled energy",
        "Verified facility-energy reduction",
        "Reproducible annual reduction",
        "Comfort-proxy change",
        "Peak demand",
        "Cost reduction",
        "Carbon reduction",
        "Safety scenarios",
        "Severe / fatal errors",
    } <= labels
    text = " ".join(
        str(item.value) for item in (*app.markdown, *app.caption, *app.info)
    )
    assert "Conservative single-zone EnergyPlus proof of concept" in text
    assert "SPACE1-1" in text
    assert "Deterministic safety authority" in text

