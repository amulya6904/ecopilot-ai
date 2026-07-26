from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_default_product_render_does_not_call_live_services(monkeypatch):
    async def fail_agent(*args, **kwargs):
        raise AssertionError("LLM agent must not run during page render")

    def fail_energyplus(*args, **kwargs):
        raise AssertionError("EnergyPlus must not run during page render")

    monkeypatch.setattr("llm.agent.AdvisoryAgent.run", fail_agent)
    monkeypatch.setattr(
        "backends.energyplus.EnergyPlusBackend.run_simulation",
        fail_energyplus,
    )
    app = AppTest.from_file("app.py", default_timeout=180).run()
    assert not app.exception
    for page in (
        "app_pages/ai_copilot.py",
        "app_pages/energyplus.py",
        "app_pages/safety.py",
    ):
        app.switch_page(page).run(timeout=180)
        assert not app.exception


def test_product_wrappers_have_no_expensive_module_level_calls():
    for path in Path("app_pages").glob("*.py"):
        if path.stem in {
            "command_center",
            "ai_copilot",
            "building",
            "analytics",
            "decisions",
            "safety",
            "energyplus",
            "reports",
            "guided_demo",
        }:
            source = path.read_text(encoding="utf-8")
            assert "run_simulation(" not in source
            assert "AdvisoryAgent(" not in source
            assert "run_fault_injection_suite(" not in source

