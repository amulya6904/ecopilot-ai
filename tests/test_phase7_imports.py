import importlib


def test_phase7_imports_without_running_ollama():
    for name in (
        "llm", "llm.agent", "llm.client", "llm.mcp_client", "llm.validator",
        "ui.phase7", "app",
    ):
        assert importlib.import_module(name)


def test_import_has_no_agent_run_side_effect(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    importlib.reload(importlib.import_module("llm.agent"))
    assert not (tmp_path / "results").exists()
