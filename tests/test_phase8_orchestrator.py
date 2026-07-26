from pathlib import Path

import energyplus.runtime_control.orchestrator as orchestrator


def test_orchestrator_uses_manual_classification(monkeypatch):
    captured = {}
    def fake(provider, **kwargs):
        captured.update(kwargs)
        return object()
    monkeypatch.setattr(orchestrator, "run_phase8_runtime", fake)
    orchestrator.run_manual_validation()
    assert captured["classification"] == "manual_energyplus_actuator_validation"
