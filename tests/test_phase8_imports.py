import importlib


def test_phase8_modules_import_without_starting_energyplus():
    for name in (
        "action_provider", "actuator_discovery", "api_loader", "artifacts",
        "audit", "callbacks", "fallback", "handles", "orchestrator",
        "runtime_runner", "schemas", "settings", "telemetry", "validator",
        "variable_discovery",
    ):
        importlib.import_module(f"energyplus.runtime_control.{name}")
