"""Public EnergyPlus installation discovery API."""

from energyplus.adapter.discovery import EnergyPlusAvailability, discover_energyplus
from energyplus.adapter.runner import EnergyPlusRunResult, run_energyplus
from energyplus.adapter.output_requests import (
    ensure_phase4_output_requests,
    inspect_output_requests,
)
from energyplus.adapter.telemetry import (
    EnergyPlusTelemetry,
    EnergyPlusTelemetrySummary,
    parse_energyplus_csv,
    parse_energyplus_outputs,
    summarize_energyplus_telemetry,
)

__all__ = [
    "EnergyPlusAvailability",
    "discover_energyplus",
    "EnergyPlusRunResult",
    "run_energyplus",
    "ensure_phase4_output_requests",
    "inspect_output_requests",
    "EnergyPlusTelemetry",
    "EnergyPlusTelemetrySummary",
    "parse_energyplus_csv",
    "parse_energyplus_outputs",
    "summarize_energyplus_telemetry",
]
