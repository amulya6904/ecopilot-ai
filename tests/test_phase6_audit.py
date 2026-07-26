import json
from concurrent.futures import ThreadPoolExecutor
from mcp_service.audit import AuditLogger, sanitize_inputs


def test_audit_success_concurrency_and_sanitization(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(pool.map(lambda i: logger.write({"audit_id": str(i), "tool_name": "x"}), range(20)))
    assert len(logger.latest(100)) == 20
    assert sanitize_inputs({"model_path": "secret", "limit": 2})["model_path"] == "[REDACTED]"
    assert "payload" not in json.dumps(logger.latest())
