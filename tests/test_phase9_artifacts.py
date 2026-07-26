import json

from safety.artifacts import REQUIRED_SAFETY_ARTIFACTS, SafetyArtifacts
from safety.fault_injection import make_candidate, make_state
from safety.schemas import SafetyHistory
from safety.settings import SafetySettings
from safety.supervisor import evaluate_action_safety


def test_phase9_writes_complete_artifact_bundle(tmp_path):
    settings = SafetySettings(repository_root=tmp_path)
    artifacts = SafetyArtifacts(
        "test", run_id="phase9-test-run", settings=settings
    )
    state = make_state(run_id="phase9-test-run")
    candidate = make_candidate(run_id="phase9-test-run")
    decision = evaluate_action_safety(
        state, candidate, settings=settings, history=SafetyHistory()
    )
    artifacts.add_decision(state, candidate, decision)
    directory = artifacts.finalize()
    assert all((directory / name).is_file() for name in REQUIRED_SAFETY_ARTIFACTS)
    summary = json.loads((directory / "summary.json").read_text())
    assert summary["classification"] == (
        "safety_supervised_energyplus_runtime_validation"
    )
    assert summary["safety_supervisor_enabled"] is True
    assert summary["final_optimization_result"] is False
    assert summary["savings_result"] is False
