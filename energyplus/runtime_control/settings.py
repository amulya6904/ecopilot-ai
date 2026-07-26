"""Frozen and repository-bounded Phase 8 runtime settings."""

from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(frozen=True)
class Phase8Settings:
    repository_root: Path = field(default_factory=lambda: Path(__file__).parents[2])
    installation_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("ENERGYPLUS_HOME", r"C:\EnergyPlusV26-1-0")
        )
    )
    source_model_path: Path = Path(
        "energyplus/models/baseline/phase5_baseline.idf"
    )
    runtime_model_path: Path = Path(
        "energyplus/models/baseline/phase5_baseline.idf"
    )
    weather_file_path: Path = Path("energyplus/weather/phase4_weather.epw")
    output_root: Path = Path("energyplus/output/official/phase8")
    artifact_root: Path = Path("results/closed_loop/phase8")
    audit_path: Path = Path("results/audit/phase8_control_events.jsonl")
    official_inventory_path: Path = Path(
        "results/official/phase8_actuator_inventory.json"
    )
    controlled_zone: str = "SPACE1-1"
    controlled_zone_alias: str = "Open Office"
    controlled_schedule_name: str = "ECOPILOT_BASELINE_COOLING_SCHEDULE"
    decision_interval_minutes: int = 60
    maximum_setpoint_change_c: float = 1.0
    minimum_cooling_setpoint_c: float = 20.0
    maximum_cooling_setpoint_c: float = 28.0
    minimum_heating_cooling_deadband_c: float = 1.0
    minimum_hold_minutes: int = 60
    fallback_policy: str = "phase5_baseline"
    action_stale_after_minutes: int = 90
    maximum_consecutive_agent_failures: int = 2
    manual_test_value_c: float = 23.0
    manual_test_duration_minutes: int = 60
    enable_manual_control: bool = True
    enable_mock_agent: bool = True
    enable_real_llm: bool = False
    llm_timeout_seconds: int = 240
    llm_assisted_validation_intervals: int = 3
    verification_tolerance_c: float = 0.15
    final_savings_result: bool = False

    def __post_init__(self) -> None:
        root = Path(self.repository_root).resolve()
        for label, path in (
            ("source model", self.source_model_path),
            ("runtime model", self.runtime_model_path),
            ("weather file", self.weather_file_path),
        ):
            resolved = self.resolve(path)
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"Phase 8 {label} must remain inside the repository.")
        for label, path in (
            ("output root", self.output_root),
            ("artifact root", self.artifact_root),
            ("audit path", self.audit_path),
            ("inventory path", self.official_inventory_path),
        ):
            resolved = self.resolve(path)
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"Phase 8 {label} must remain inside the repository.")
        if not self.controlled_zone.strip() or not self.controlled_zone_alias.strip():
            raise ValueError("Controlled zone and alias are required.")
        if self.decision_interval_minutes < 60:
            raise ValueError("Phase 8 decision interval must be at least 60 minutes.")
        if self.action_stale_after_minutes < self.decision_interval_minutes:
            raise ValueError("Action staleness must not precede the decision interval.")
        if self.minimum_hold_minutes <= 0:
            raise ValueError("Minimum hold time must be positive.")
        if not (
            self.minimum_cooling_setpoint_c
            < self.maximum_cooling_setpoint_c
        ):
            raise ValueError("Cooling setpoint bounds are invalid.")
        if not (
            self.minimum_cooling_setpoint_c
            <= self.manual_test_value_c
            <= self.maximum_cooling_setpoint_c
        ):
            raise ValueError("Manual test value is outside the Phase 8 bounds.")
        if self.maximum_setpoint_change_c <= 0:
            raise ValueError("Maximum setpoint change must be positive.")
        if self.minimum_heating_cooling_deadband_c <= 0:
            raise ValueError("Heating/cooling deadband must be positive.")
        if self.manual_test_duration_minutes < self.minimum_hold_minutes:
            raise ValueError("Manual test duration is shorter than minimum hold time.")
        if self.maximum_consecutive_agent_failures < 1:
            raise ValueError("Maximum agent failures must be positive.")
        if self.llm_assisted_validation_intervals < 3:
            raise ValueError(
                "LLM-assisted validation requires apply, maintain, and reset intervals."
            )
        if self.fallback_policy != "phase5_baseline":
            raise ValueError("Phase 8 supports only the Phase 5 baseline fallback.")
        if self.final_savings_result:
            raise ValueError("Phase 8 cannot be classified as a savings result.")

    def resolve(self, path: Path) -> Path:
        candidate = Path(path)
        return (
            candidate.resolve()
            if candidate.is_absolute()
            else (Path(self.repository_root) / candidate).resolve()
        )

    def validate_runtime_paths(self) -> tuple[str, ...]:
        issues: list[str] = []
        for label, path in (
            ("source model", self.resolve(self.source_model_path)),
            ("runtime model", self.resolve(self.runtime_model_path)),
            ("weather file", self.resolve(self.weather_file_path)),
        ):
            if not path.is_file():
                issues.append(f"Phase 8 {label} does not exist: {path}")
        if not Path(self.installation_root).is_dir():
            issues.append(
                f"EnergyPlus installation root does not exist: "
                f"{self.installation_root}"
            )
        return tuple(issues)


PHASE8_SETTINGS = Phase8Settings()

__all__ = ["PHASE8_SETTINGS", "Phase8Settings"]
