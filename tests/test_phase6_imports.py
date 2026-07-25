import importlib


def test_imports_are_side_effect_free():
    for module in (
        "mcp_service", "mcp_service.server", "mcp_service.settings",
        "mcp_service.context", "scripts.run_phase6_mcp_server",
        "scripts.test_phase6_mcp_client",
    ):
        assert importlib.import_module(module)
