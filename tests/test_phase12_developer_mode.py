from streamlit.testing.v1 import AppTest


def test_developer_mode_is_off_by_default_and_preserves_phase_routes():
    app = AppTest.from_file("app.py", default_timeout=120).run()
    assert app.sidebar.toggle[1].label == "Developer Mode"
    assert app.sidebar.toggle[1].value is False
    app.sidebar.toggle[1].set_value(True).run(timeout=120)
    assert not app.exception
    assert app.sidebar.toggle[0].value is False
    app.switch_page("app_pages/phase11.py").run(timeout=120)
    assert not app.exception
    app.switch_page("app_pages/phase7.py").run(timeout=120)
    assert not app.exception
    assert "Generate Advisory Proposal" in {button.label for button in app.button}

