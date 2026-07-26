from streamlit.testing.v1 import AppTest


def test_judge_mode_is_default_and_locks_expensive_phase_controls():
    app = AppTest.from_file("app.py", default_timeout=60).run()
    assert not app.exception
    assert app.sidebar.toggle[0].label == "Judge Mode"
    assert app.sidebar.toggle[0].value is True
    for page in (
        "app_pages/phase2.py",
        "app_pages/phase4.py",
        "app_pages/phase7.py",
        "app_pages/phase8.py",
        "app_pages/phase9.py",
    ):
        app.switch_page(page).run(timeout=60)
        assert not app.exception
        assert not app.button


def test_developer_mode_retains_clear_explicit_controls():
    app = AppTest.from_file("app.py", default_timeout=60).run()
    app.sidebar.toggle[0].set_value(False).run(timeout=60)
    expected = {
        "app_pages/phase2.py": "Run Development Simulator",
        "app_pages/phase4.py": "Run EnergyPlus Integration Validation",
        "app_pages/phase6.py": "Validate MCP Tools",
        "app_pages/phase7.py": "Generate Advisory Proposal",
        "app_pages/phase8.py": "Run Closed-Loop Validation",
        "app_pages/phase9.py": "Run Safety Test Suite",
    }
    for page, label in expected.items():
        app.switch_page(page).run(timeout=60)
        assert not app.exception
        assert label in {button.label for button in app.button}
