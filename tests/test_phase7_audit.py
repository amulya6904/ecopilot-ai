import json
from dataclasses import replace

from llm.audit import AgentAuditWriter
from llm.settings import LLM_SETTINGS


def test_success_and_failure_audit_records(tmp_path):
    settings = replace(LLM_SETTINGS, repository_root=tmp_path)
    writer = AgentAuditWriter(settings)
    assert writer.append_audit({
        "final_status": "success", "tool_call_sequence": ["list_zones"],
        "secret": None,
    })
    assert writer.append_audit({"final_status": "failed", "error_code": "test"})
    records = [
        json.loads(line)
        for line in settings.resolve(settings.agent_audit_path).read_text().splitlines()
    ]
    assert records[0]["tool_call_sequence"] == ["list_zones"]
    assert records[1]["final_status"] == "failed"
    assert "token" not in settings.resolve(settings.agent_audit_path).read_text().casefold()


def test_detailed_artifacts_written_separately(tmp_path):
    settings = replace(LLM_SETTINGS, repository_root=tmp_path)
    path = AgentAuditWriter(settings).write_artifacts(
        "safe-run-id", {"run_metadata.json": {"success": True}, "final_response.txt": "{}"}
    )
    assert (path / "run_metadata.json").is_file()
    assert (path / "final_response.txt").is_file()
