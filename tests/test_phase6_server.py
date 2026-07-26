import asyncio
from mcp_service.server import create_mcp_server


def test_server_creation_does_not_run_and_catalogue_is_exact(phase6_context):
    server = create_mcp_server(phase6_context)
    tools = asyncio.run(server.list_tools())
    assert len(tools) == 16
    assert "run_official_baseline" in {tool.name for tool in tools}
    assert not any("setpoint" in tool.name or "actuator" in tool.name for tool in tools)
