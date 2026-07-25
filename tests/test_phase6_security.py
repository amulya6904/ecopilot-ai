from pathlib import Path
from mcp_service.schemas import BaselineRunRequest
from mcp_service.server import create_mcp_server


def test_no_dangerous_constructs_or_control_tools(phase6_context):
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("mcp_service").rglob("*.py")
    )
    assert "shell=True" not in source
    assert "eval(" not in source
    assert "exec(" not in source
    assert "setpoint_modification" not in source
    assert BaselineRunRequest.model_json_schema()["additionalProperties"] is False
