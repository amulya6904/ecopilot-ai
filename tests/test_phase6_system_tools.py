from mcp_service.tools.system_tools import get_available_outputs, get_system_status


def test_system_and_outputs(phase6_context):
    status = get_system_status(phase6_context)
    assert status["success"] and status["data"]["control_tools_enabled"] is False
    assert get_available_outputs(phase6_context)["data"]["pmv"]["available"] is False
