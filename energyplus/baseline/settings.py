"""Authoritative immutable configuration for the official Phase 5 baseline."""

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from config.settings import HVAC


ENERGYPLUS_ZONE_DISPLAY_NAMES: Mapping[str, str] = MappingProxyType({
    "SPACE1-1": "Open Office",
    "SPACE2-1": "Conference Room",
    "SPACE3-1": "Computer Lab",
    "SPACE4-1": "Support Zone",
    "SPACE5-1": "Auxiliary Zone",
    "PLENUM-1": "HVAC Plenum",
})

ENERGYPLUS_ZONE_ROLES: Mapping[str, str] = MappingProxyType({
    "SPACE1-1": "primary_occupied",
    "SPACE2-1": "primary_occupied",
    "SPACE3-1": "primary_occupied",
    "SPACE4-1": "support_occupied",
    "SPACE5-1": "auxiliary_occupied",
    "PLENUM-1": "plenum",
})


@dataclass(frozen=True)
class EnergyPlusBaselineSettings:
    """Frozen conventional policy and repository paths for the Phase 5 baseline."""

    occupied_start_hour: int = 9
    occupied_end_hour: int = 18
    occupied_cooling_setpoint_c: float = 22.0
    unoccupied_cooling_setpoint_c: float = 27.0
    occupied_heating_setpoint_c: float = 20.0
    unoccupied_heating_setpoint_c: float = 16.0
    occupied_temperature_min_c: float = 22.0
    occupied_temperature_max_c: float = 25.0
    pmv_min: float = -0.5
    pmv_max: float = 0.5
    reporting_frequency: str = "Hourly"
    reproducibility_tolerance: float = 1e-6
    thermostat_tolerance_c: float = 1e-6
    repository_root: Path = field(
        default_factory=lambda: Path(__file__).parents[2]
    )
    base_model_path: Path = Path(
        "energyplus/models/modified/phase4_telemetry_model.idf"
    )
    baseline_model_path: Path = Path(
        "energyplus/models/baseline/phase5_baseline.idf"
    )
    weather_file_path: Path = Path("energyplus/weather/phase4_weather.epw")
    official_output_root: Path = Path("energyplus/output/official/baseline")
    official_results_root: Path = Path("results/official")
    metadata_root: Path = Path("energyplus/metadata/baseline")
    zone_display_names: Mapping[str, str] = field(
        default_factory=lambda: ENERGYPLUS_ZONE_DISPLAY_NAMES
    )
    zone_roles: Mapping[str, str] = field(
        default_factory=lambda: ENERGYPLUS_ZONE_ROLES
    )

    def __post_init__(self) -> None:
        if not 0 <= self.occupied_start_hour < self.occupied_end_hour <= 24:
            raise ValueError("Occupied start must be before occupied end.")
        for heating, cooling in (
            (self.occupied_heating_setpoint_c, self.occupied_cooling_setpoint_c),
            (self.unoccupied_heating_setpoint_c, self.unoccupied_cooling_setpoint_c),
        ):
            if heating >= cooling:
                raise ValueError("Heating setpoint must remain below cooling setpoint.")
        if (
            self.unoccupied_cooling_setpoint_c
            < self.occupied_cooling_setpoint_c
        ):
            raise ValueError(
                "Unoccupied cooling setpoint cannot be below occupied cooling."
            )
        if (
            self.occupied_temperature_min_c
            >= self.occupied_temperature_max_c
        ):
            raise ValueError("Occupied comfort minimum must be below maximum.")
        if self.pmv_min >= self.pmv_max:
            raise ValueError("PMV minimum must be below maximum.")
        if self.reporting_frequency.casefold() not in {
            "hourly", "timestep", "daily", "monthly", "runperiod"
        }:
            raise ValueError("Unsupported EnergyPlus reporting frequency.")
        if self.reproducibility_tolerance < 0 or self.thermostat_tolerance_c < 0:
            raise ValueError("Baseline tolerances must be non-negative.")
        if any(
            not -60.0 <= value <= 200.0
            for value in (
                self.occupied_heating_setpoint_c,
                self.unoccupied_heating_setpoint_c,
                self.occupied_cooling_setpoint_c,
                self.unoccupied_cooling_setpoint_c,
            )
        ):
            raise ValueError("Baseline setpoint is outside the model temperature limits.")
        if any(
            not HVAC.minimum_setpoint_c <= value <= HVAC.maximum_setpoint_c
            for value in (
                self.occupied_cooling_setpoint_c,
                self.unoccupied_cooling_setpoint_c,
            )
        ):
            raise ValueError("Baseline cooling setpoint is outside HVAC limits.")
        root = Path(self.repository_root).resolve()
        source = self.resolve(self.base_model_path)
        destination = self.resolve(self.baseline_model_path)
        if source == destination:
            raise ValueError("Source and baseline model paths must differ.")
        for label, path in (
            ("Baseline model", destination),
            ("Official output", self.resolve(self.official_output_root)),
            ("Official results", self.resolve(self.official_results_root)),
            ("Metadata", self.resolve(self.metadata_root)),
        ):
            if path != root and root not in path.parents:
                raise ValueError(f"{label} path must remain inside the repository.")
        models_root = (root / "energyplus" / "models").resolve()
        if destination != models_root and models_root not in destination.parents:
            raise ValueError("Baseline model must be written under energyplus/models.")
        display_keys = {key.casefold() for key in self.zone_display_names}
        role_keys = {key.casefold() for key in self.zone_roles}
        if display_keys != role_keys:
            raise ValueError("Zone display-name and role mappings must share keys.")

    def resolve(self, path: Path) -> Path:
        """Resolve a configured path relative to the repository root."""
        candidate = Path(path)
        return (
            candidate.resolve()
            if candidate.is_absolute()
            else (Path(self.repository_root) / candidate).resolve()
        )


ENERGYPLUS_BASELINE = EnergyPlusBaselineSettings()

__all__ = [
    "ENERGYPLUS_BASELINE",
    "ENERGYPLUS_ZONE_DISPLAY_NAMES",
    "ENERGYPLUS_ZONE_ROLES",
    "EnergyPlusBaselineSettings",
]
