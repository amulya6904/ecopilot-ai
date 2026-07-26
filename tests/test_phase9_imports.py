import importlib


def test_phase9_and_earlier_runtime_import_without_execution():
    modules = [
        "safety",
        "safety.artifacts",
        "safety.fault_injection",
        "energyplus.runtime_control",
        "llm",
        "mcp_service",
        "scripts.run_phase9_safety_validation",
    ]
    for name in modules:
        assert importlib.import_module(name)
