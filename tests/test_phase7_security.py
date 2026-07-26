from pathlib import Path

from llm.mcp_client import MODEL_TOOL_ALLOWLIST


def test_no_execution_or_actuator_tools_exposed():
    forbidden = ("run_official_baseline", "actuator", "apply", "execute", "control")
    assert all(not any(word in tool for word in forbidden) for tool in MODEL_TOOL_ALLOWLIST)


def test_no_shell_or_dynamic_execution_in_phase7_source():
    root = Path(__file__).parents[1]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "llm").glob("*.py")
    )
    assert "shell=True" not in source
    assert "eval(" not in source
    assert "exec(" not in source


def test_model_tool_schemas_offer_no_paths_or_commands():
    forbidden = ("path", "command", "script", "environment", "actuator")
    assert all(not any(word in name for word in forbidden) for name in MODEL_TOOL_ALLOWLIST)
