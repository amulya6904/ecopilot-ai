"""Backend registry with explicit, non-fallback construction."""

from typing import Any

from backends.base import BuildingBackend
from backends.energyplus import EnergyPlusBackend
from backends.lightweight import LightweightSimulatorBackend


def get_backend_status() -> dict[str, dict[str, object]]:
    """Return installation and full-readiness states separately."""
    energyplus = EnergyPlusBackend()
    status = energyplus.availability_status()
    return {
        "lightweight": {
            "available": True,
            "label": "Lightweight Development Simulator",
        },
        "energyplus": {
            "available": status.ready_for_run,
            "installed": status.installed,
            "label": energyplus.display_name,
            "reason": status.reason,
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
