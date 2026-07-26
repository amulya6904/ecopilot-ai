"""Frozen, validated settings for the official Phase 10 comparison."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ComparisonSettings:
    """Scientific comparison, claim-gate, and derived-metric assumptions."""

    repository_root: Path = field(
        default_factory=lambda: Path(__file__).parents[1]
    )
    baseline_artifact_selector: str = "latest_successful"
    controlled_artifact_selector: str = "latest_successful"
    required_backend: str = "energyplus"
    required_source: str = "EnergyPlus"
    minimum_comfort_compliance_percent: float = 20.0
    maximum_allowed_comfort_degradation_percent: float = 1.0
    energy_tolerance_kwh: float = 1e-6
    demand_tolerance_kw: float = 1e-6
    comfort_tolerance_percent: float = 1e-6
    reproducibility_tolerance: float = 1e-6
    electricity_tariff_mode: Literal["flat", "time_of_use"] = "flat"
    flat_tariff_per_kwh: float = 8.0
    currency: str = "INR"
    tariff_source: str = (
        "Phase 10 project assumption; replace with the applicable utility tariff."
    )
    time_of_use_tariff_by_hour: tuple[float, ...] | None = None
    carbon_intensity_mode: Literal["constant", "time_varying"] = "constant"
    constant_carbon_intensity_g_per_kwh: float = 708.0
    carbon_intensity_source: str = (
        "Phase 10 project assumption; replace with a cited grid factor."
    )
    time_varying_carbon_g_per_kwh_by_hour: tuple[float, ...] | None = None
    demand_warning_kw: float = 18.0
    demand_critical_kw: float = 30.0
    require_complete_horizon: bool = True
    require_zero_fatal_errors: bool = True
    require_zero_severe_errors: bool = True
    allow_conditionally_comparable: bool = False
    controlled_setpoint_step_c: float = 0.5
    occupied_temperature_min_c: float = 22.0
    occupied_temperature_max_c: float = 25.0
    pmv_min: float = -0.5
    pmv_max: float = 0.5
    comparison_artifact_root: Path = Path("results/comparison/phase10")
    controlled_artifact_root: Path = Path("results/closed_loop/phase8")
    controlled_output_root: Path = Path("energyplus/output/official/phase8")

    def __post_init__(self) -> None:
        if not self.baseline_artifact_selector.strip():
            raise ValueError("Baseline artifact selector is required.")
        if not self.controlled_artifact_selector.strip():
            raise ValueError("Controlled artifact selector is required.")
        if self.required_backend.casefold() != "energyplus":
            raise ValueError("Official Phase 10 comparisons require EnergyPlus.")
        if self.required_source != "EnergyPlus":
            raise ValueError("Official Phase 10 source must be EnergyPlus.")
        for label, value in (
            (
                "minimum comfort compliance",
                self.minimum_comfort_compliance_percent,
            ),
            (
                "maximum comfort degradation",
                self.maximum_allowed_comfort_degradation_percent,
            ),
            ("comfort tolerance", self.comfort_tolerance_percent),
        ):
            if not 0 <= value <= 100:
                raise ValueError(f"{label.title()} must be between 0 and 100.")
        for label, value in (
            ("energy tolerance", self.energy_tolerance_kwh),
            ("demand tolerance", self.demand_tolerance_kw),
            ("reproducibility tolerance", self.reproducibility_tolerance),
        ):
            if value < 0:
                raise ValueError(f"{label.title()} must be non-negative.")
        if self.electricity_tariff_mode == "flat":
            if self.flat_tariff_per_kwh < 0:
                raise ValueError("Flat electricity tariff must be non-negative.")
        elif (
            self.time_of_use_tariff_by_hour is None
            or len(self.time_of_use_tariff_by_hour) != 24
            or any(value < 0 for value in self.time_of_use_tariff_by_hour)
        ):
            raise ValueError(
                "Time-of-use mode requires 24 non-negative hourly tariffs."
            )
        if self.carbon_intensity_mode == "constant":
            if self.constant_carbon_intensity_g_per_kwh < 0:
                raise ValueError("Constant carbon intensity must be non-negative.")
        elif (
            self.time_varying_carbon_g_per_kwh_by_hour is None
            or len(self.time_varying_carbon_g_per_kwh_by_hour) != 24
            or any(
                value < 0
                for value in self.time_varying_carbon_g_per_kwh_by_hour
            )
        ):
            raise ValueError(
                "Time-varying mode requires 24 non-negative hourly intensities."
            )
        if not 0 < self.demand_warning_kw < self.demand_critical_kw:
            raise ValueError(
                "Demand warning threshold must be below the critical threshold."
            )
        if not 0 < self.controlled_setpoint_step_c <= 1.0:
            raise ValueError(
                "The deterministic controlled setpoint step must be in (0, 1]."
            )
        if not (
            self.occupied_temperature_min_c
            < self.occupied_temperature_max_c
        ):
            raise ValueError("Occupied comfort bounds must be ordered.")
        if self.pmv_min >= self.pmv_max:
            raise ValueError("PMV bounds must be ordered.")
        if not self.currency.strip():
            raise ValueError("Currency is required.")
        root = Path(self.repository_root).resolve()
        for label, path in (
            ("comparison artifact root", self.comparison_artifact_root),
            ("controlled artifact root", self.controlled_artifact_root),
            ("controlled output root", self.controlled_output_root),
        ):
            resolved = self.resolve(path)
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"{label.title()} must remain in the repository.")

    def resolve(self, path: Path) -> Path:
        """Resolve a repository-relative comparison path."""

        candidate = Path(path)
        return (
            candidate.resolve()
            if candidate.is_absolute()
            else (Path(self.repository_root) / candidate).resolve()
        )


COMPARISON_SETTINGS = ComparisonSettings()

__all__ = ["COMPARISON_SETTINGS", "ComparisonSettings"]
