import asyncio
from mcp_service.server import create_mcp_server


def test_resources_discoverable_and_bounded(phase6_context):
    server = create_mcp_server(phase6_context)
    resources = asyncio.run(server.list_resources())
    assert len(resources) == 6
    assert all(item.mimeType == "application/json" for item in resources)
