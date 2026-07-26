from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.demo.safety_center import _run_unsafe_demo


def test_unsafe_proposal_uses_deterministic_fault_suite_without_actuator():
    result = _run_unsafe_demo("Out-of-range setpoint")
    assert result is not None
    assert result["passed"] is True
    assert result["actual_outcome"] in {
        "approve_with_clamp",
        "reject",
        "hold",
        "fallback",
    }
    source = Path("ui/demo/safety_center.py").read_text(encoding="utf-8")
    assert "run_fault_injection_suite" in source
    assert "set_actuator_value" not in source
    assert "api.exchange" not in source


def test_safety_center_renders_22_of_22_and_explicit_demo():
    app = AppTest.from_file("app.py", default_timeout=180).run()
    app.switch_page("app_pages/safety.py").run(timeout=180)
    assert not app.exception
    values = {str(metric.value) for metric in app.metric}
    assert "22/22" in values
    assert "Test Unsafe Proposal" in {button.label for button in app.button}
