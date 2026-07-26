"""Frozen Phase 9 prototype safety thresholds and repository-bounded paths."""

from dataclasses import dataclass, field
from pathlib import Path

from energyplus.runtime_control.settings import PHASE8_SETTINGS


@dataclass(frozen=True)
class SafetySettings:
    repository_root: Path = field(
        default_factory=lambda: Path(__file__).parents[1]
    )
    artifact_root: Path = Path("results/safety/phase9")
    audit_path: Path = Path("results/audit/phase9_safety_events.jsonl")

    occupied_temperature_min_c: float = 22.0
    occupied_temperature_max_c: float = 25.0
    unoccupied_temperature_min_c: float = 16.0
    unoccupied_temperature_max_c: float = 30.0
    emergency_temperature_min_c: float = 10.0
    emergency_temperature_max_c: float = 35.0

    pmv_min: float = -0.5
    pmv_max: float = 0.5
    ppd_warning_percent: float = 20.0
    ppd_critical_percent: float = 50.0
    require_pmv_when_available: bool = True
    allow_temperature_proxy: bool = True

    minimum_cooling_setpoint_c: float = (
        PHASE8_SETTINGS.minimum_cooling_setpoint_c
    )
    maximum_cooling_setpoint_c: float = (
        PHASE8_SETTINGS.maximum_cooling_setpoint_c
    )
    maximum_setpoint_change_c: float = (
        PHASE8_SETTINGS.maximum_setpoint_change_c
    )
    minimum_heating_cooling_deadband_c: float = (
        PHASE8_SETTINGS.minimum_heating_cooling_deadband_c
    )
    minimum_hold_minutes: int = PHASE8_SETTINGS.minimum_hold_minutes
    maximum_actions_per_zone_per_hour: int = 4
    setpoint_match_tolerance_c: float = (
        PHASE8_SETTINGS.verification_tolerance_c
    )
    allow_baseline_heating_proxy: bool = True
    baseline_heating_setpoint_c: float = 16.0

    # Prototype project thresholds pending final calibration.
    demand_warning_kw: float = 24.0
    demand_critical_kw: float = 30.0

    maximum_telemetry_age_seconds: float = 300.0
    maximum_missing_samples: int = 2
    maximum_consecutive_agent_failures: int = (
        PHASE8_SETTINGS.maximum_consecutive_agent_failures
    )
    maximum_actuator_verification_failures: int = 2
    maximum_rollbacks_before_emergency: int = 2
    oscillation_reversal_limit: int = 2

    fallback_policy: str = "phase5_baseline"
    emergency_disable_autonomy: bool = True
    operator_acknowledgement_required_after_emergency: bool = True
    safety_supervisor_enabled: bool = True
    deterministic_safety_authority: bool = True
    autonomous_bypass_allowed: bool = False

    def __post_init__(self) -> None:
        if not (
            self.emergency_temperature_min_c
            <= self.unoccupied_temperature_min_c
            <= self.occupied_temperature_min_c
            < self.occupied_temperature_max_c
            <= self.unoccupied_temperature_max_c
            <= self.emergency_temperature_max_c
        ):
            raise ValueError(
                "Comfort ranges must be ordered inside emergency limits."
            )
        if self.pmv_min >= self.pmv_max:
            raise ValueError("PMV limits must be ordered.")
        if not 0 <= self.ppd_warning_percent < self.ppd_critical_percent <= 100:
            raise ValueError("PPD thresholds are invalid.")
        if not (
            self.minimum_cooling_setpoint_c
            < self.maximum_cooling_setpoint_c
        ):
            raise ValueError("Cooling setpoint bounds are invalid.")
        if not 0 < self.maximum_setpoint_change_c:
            raise ValueError("Maximum setpoint change must be positive.")
        if self.minimum_heating_cooling_deadband_c <= 0:
            raise ValueError("Deadband must be positive.")
        if not 0 < self.demand_warning_kw < self.demand_critical_kw:
            raise ValueError(
                "Demand warning must be below the critical threshold."
            )
        if self.maximum_telemetry_age_seconds <= 0:
            raise ValueError("Telemetry freshness limit must be positive.")
        if (
            self.maximum_actions_per_zone_per_hour < 1
            or self.minimum_hold_minutes < 1
        ):
            raise ValueError("Action rate and hold limits must be positive.")
        if (
            not self.safety_supervisor_enabled
            or not self.deterministic_safety_authority
            or self.autonomous_bypass_allowed
        ):
            raise ValueError(
                "Phase 9 autonomous execution cannot bypass safety supervision."
            )
        if self.fallback_policy != "phase5_baseline":
            raise ValueError("Only the verified Phase 5 baseline fallback is allowed.")
        root = Path(self.repository_root).resolve()
        for label, path in (
            ("artifact root", self.artifact_root),
            ("audit path", self.audit_path),
        ):
            resolved = self.resolve(path)
            if resolved != root and root not in resolved.parents:
                raise ValueError(
                    f"Phase 9 {label} must remain inside the repository."
                )

    def resolve(self, path: Path) -> Path:
        candidate = Path(path)
        return (
            candidate.resolve()
            if candidate.is_absolute()
            else (Path(self.repository_root) / candidate).resolve()
        )


SAFETY_SETTINGS = SafetySettings()

__all__ = ["SAFETY_SETTINGS", "SafetySettings"]
