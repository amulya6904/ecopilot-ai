"""Discover and print real Phase 8 EnergyPlus actuator candidates."""

import json

from energyplus.runtime_control.actuator_discovery import (
    discover_available_actuators,
)


def main() -> int:
    result = discover_available_actuators()
    print(f"Success: {result['success']}")
    print(f"Inventory count: {result.get('inventory_count', 0)}")
    print("Confirmed schedule/thermostat cooling candidates:")
    for item in result.get("candidates", []):
        print(f"  {item['identifier']} [{item['unit']}]")
    print("Selected actuator:")
    print(json.dumps(result.get("selected_actuator"), indent=2))
    print(f"Artifact: {result.get('artifact_path')}")
    for error in result.get("errors", []):
        print(f"ERROR: {error}")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
