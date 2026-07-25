from pathlib import Path
import pytest
from mcp_service.settings import MCPSettings


def test_valid_defaults_and_safe_paths(tmp_path):
    settings = MCPSettings(repository_root=tmp_path)
    assert settings.control_tools_enabled is False
    assert settings.resolve(settings.audit_log_path).is_relative_to(tmp_path)


def test_invalid_limits_and_controls(tmp_path):
    with pytest.raises(ValueError):
        MCPSettings(repository_root=tmp_path, max_telemetry_records=0)
    with pytest.raises(ValueError):
        MCPSettings(repository_root=tmp_path, control_tools_enabled=True)
    with pytest.raises(ValueError):
        MCPSettings(repository_root=tmp_path, audit_log_path=Path(tmp_path).parent / "escape.jsonl")
