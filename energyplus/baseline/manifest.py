"""Frozen input identity and manifest helpers for the official baseline."""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from energyplus.baseline.schedule_inspector import BaselineModelInspection


GENERATOR_VERSION = "ecopilot-phase5-v1"


def calculate_sha256(path: Path) -> str:
    """Calculate a stable SHA-256 digest without loading a large file at once."""
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_baseline_manifest(
    *,
    run_id: str,
    energyplus_version: str | None,
    executable_path: Path | None,
    base_model_path: Path,
    base_model_hash: str,
    derived_model_path: Path,
    derived_model_hash: str,
    weather_path: Path,
    weather_hash: str,
    reporting_frequency: str,
    inspection: BaselineModelInspection,
    thermostat_policy: dict[str, Any],
    zone_mapping: dict[str, str],
    zone_roles: dict[str, str],
    requested_outputs: list[str],
    actual_available_outputs: dict[str, bool],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create the JSON-safe proof of baseline input and output identity."""
    run_period = list(inspection.run_periods[0]) if inspection.run_periods else None
    return {
        "manifest_version": 1,
        "generator_version": GENERATOR_VERSION,
        "run_id": run_id,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "energyplus_version": energyplus_version,
        "executable_path": str(executable_path) if executable_path else None,
        "base_model_path": str(Path(base_model_path).resolve()),
        "base_model_hash": base_model_hash,
        "derived_baseline_model_path": str(Path(derived_model_path).resolve()),
        "derived_model_hash": derived_model_hash,
        "weather_path": str(Path(weather_path).resolve()),
        "weather_hash": weather_hash,
        "reporting_frequency": reporting_frequency,
        "simulation_period": "annual weather-file run",
        "run_period": run_period,
        "timestep": (
            list(inspection.timesteps[0]) if inspection.timesteps else None
        ),
        "occupancy_schedule_inventory": [
            {
                "people_object": item.object_name,
                "schedule": item.referenced_schedule,
                "zones": list(item.referenced_zones),
                "design_people": item.design_people,
            }
            for item in inspection.occupancy_references
        ],
        "internal_load_schedule_inventory": {
            "people": [
                {
                    "object": item.object_name,
                    "schedule": item.referenced_schedule,
                    "zones": list(item.referenced_zones),
                }
                for item in inspection.people_objects
            ],
            "lights": [
                {
                    "object": item.object_name,
                    "schedule": item.referenced_schedule,
                    "zones": list(item.referenced_zones),
                }
                for item in inspection.lights_objects
            ],
            "electric_equipment": [
                {
                    "object": item.object_name,
                    "schedule": item.referenced_schedule,
                    "zones": list(item.referenced_zones),
                }
                for item in inspection.electric_equipment_objects
            ],
        },
        "hvac_availability_schedule_inventory": [
            item.object_name for item in inspection.hvac_availability_schedules
        ],
        "thermostat_policy": thermostat_policy,
        "zone_display_mapping": zone_mapping,
        "zone_roles": zone_roles,
        "requested_outputs": requested_outputs,
        "actual_available_outputs": actual_available_outputs,
        "warnings": warnings,
    }


__all__ = [
    "GENERATOR_VERSION",
    "calculate_sha256",
    "create_baseline_manifest",
]
