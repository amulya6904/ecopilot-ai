"""Safe, import-side-effect-free EnergyPlus runtime control for Phase 8."""

from .api_loader import EnergyPlusRuntimeAvailability, inspect_runtime_availability
from .settings import PHASE8_SETTINGS, Phase8Settings


def __getattr__(name: str):
    """Load runtime entry points lazily to preserve import-side-effect safety."""

    if name in {"run_manual_validation", "run_mock_closed_loop"}:
        from .orchestrator import (
            run_manual_validation,
            run_mock_closed_loop,
        )

        return {
            "run_manual_validation": run_manual_validation,
            "run_mock_closed_loop": run_mock_closed_loop,
        }[name]
    raise AttributeError(name)

__all__ = [
    "EnergyPlusRuntimeAvailability",
    "PHASE8_SETTINGS",
    "Phase8Settings",
    "inspect_runtime_availability",
    "run_manual_validation",
    "run_mock_closed_loop",
]
