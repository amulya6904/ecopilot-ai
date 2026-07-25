"""Backend registry with explicit, non-fallback construction."""

from typing import Any

from backends.base import BuildingBackend
from backends.energyplus import EnergyPlusBackend
from backends.lightweight import LightweightSimulatorBackend


def get_backend_status() -> dict[str, dict[str, object]]:
    """Return honest availability and display labels for configured backends."""

    return {
        "lightweight": {
            "available": True,
            "label": "Lightweight Development Simulator",
        },
        "energyplus": {
            "available": False,
            "label": "EnergyPlus",
        },
    }


def create_backend(name: str, **kwargs: Any) -> BuildingBackend:
    """Create only the explicitly requested backend."""

    if name == "lightweight":
        return LightweightSimulatorBackend(**kwargs)
    if name == "energyplus":
        return EnergyPlusBackend(**kwargs)
    raise ValueError(f"Unknown building backend: {name}")


__all__ = [
    "BuildingBackend",
    "EnergyPlusBackend",
    "LightweightSimulatorBackend",
    "create_backend",
    "get_backend_status",
]
