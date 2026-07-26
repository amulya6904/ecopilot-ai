from streamlit.testing.v1 import AppTest

from ui.demo.copilot_service import SUGGESTED_QUESTIONS, build_replay_answer


def test_replay_copilot_uses_saved_evidence_without_ollama(monkeypatch):
    def fail_if_constructed(*args, **kwargs):
        raise AssertionError("Ollama must not be used for verified replay")

    monkeypatch.setattr(
        "ui.demo.copilot_service.OllamaClient",
        fail_if_constructed,
    )
    answer = build_replay_answer("Explain the measured energy savings.")
    assert answer.source_mode == "Verified artifact replay"
    assert answer.safety_classification == "Verified artifact-based response"
    assert answer.latency_seconds == 0
    assert answer.artifacts
    assert "5.626" in answer.content


def test_copilot_page_and_all_suggestions_render():
    assert len(SUGGESTED_QUESTIONS) == 10
    app = AppTest.from_file("app.py", default_timeout=120).run()
    app.switch_page("app_pages/ai_copilot.py").run(timeout=120)
    assert not app.exception
    assert [title.value for title in app.title] == ["Ask EcoPilot"]
    assert "Clear chat" in {button.label for button in app.button}
    source = open("ui/demo/ai_copilot.py", encoding="utf-8").read()
    assert "chain-of-thought" in source
    assert "copilot_messages" in source

