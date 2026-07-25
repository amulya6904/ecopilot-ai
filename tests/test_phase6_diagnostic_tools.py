from mcp_service.tools.diagnostic_tools import get_runtime_errors


def test_filtered_compact_errors(phase6_context):
    result = get_runtime_errors(phase6_context, severity="warning", limit=1)
    assert result["success"]
    assert result["data"]["records"][0]["classification"] == "reporting_issue"
    assert "raw_log_excerpt" not in result["data"]["records"][0]
