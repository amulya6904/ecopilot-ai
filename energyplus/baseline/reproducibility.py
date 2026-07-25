"""Compare two official Phase 5 runs against frozen inputs and metrics."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from energyplus.baseline.runner import EnergyPlusBaselineRunResult


@dataclass(frozen=True)
class BaselineReproducibilityReport:
    reproducible: bool
    exact_input_match: bool
    energy_absolute_difference_kwh: float | None
    energy_relative_difference_percent: float | None
    peak_demand_difference_kw: float | None
    telemetry_shape_match: bool
    warnings_match: bool
    mismatches: tuple[str, ...]
    first_run_id: str
    second_run_id: str
    tolerance: float


def _difference(first: Any, second: Any) -> float | None:
    if first is None or second is None:
        return None
    return abs(float(first) - float(second))


def _metric_match(
    first: Any,
    second: Any,
    tolerance: float,
    label: str,
    mismatches: list[str],
) -> None:
    if first is None and second is None:
        return
    if first is None or second is None:
        mismatches.append(f"{label} availability differs between runs.")
        return
    if abs(float(first) - float(second)) > tolerance:
        mismatches.append(
            f"{label} differs by {abs(float(first) - float(second)):.12g}, "
            f"above tolerance {tolerance:.12g}."
        )


def compare_baseline_runs(
    first_result: "EnergyPlusBaselineRunResult",
    second_result: "EnergyPlusBaselineRunResult",
    tolerance: float,
) -> BaselineReproducibilityReport:
    """Compare frozen identities, telemetry shapes, diagnostics, and KPIs."""
    if tolerance < 0:
        raise ValueError("Reproducibility tolerance must be non-negative.")
    first = first_result.baseline_summary
    second = second_result.baseline_summary
    mismatches: list[str] = []
    if not first_result.success or not second_result.success:
        mismatches.append("Both baseline runs must succeed.")
    input_keys = (
        "base_model_hash",
        "derived_model_hash",
        "weather_hash",
        "energyplus_version",
        "reporting_frequency",
    )
    exact_input_match = all(first.get(key) == second.get(key) for key in input_keys)
    for key in input_keys:
        if first.get(key) != second.get(key):
            mismatches.append(f"Input identity mismatch: {key}.")
    facility_shape = (
        first_result.facility_telemetry.shape
        == second_result.facility_telemetry.shape
    )
    zone_shape = (
        first_result.zone_telemetry.shape
        == second_result.zone_telemetry.shape
    )
    telemetry_shape_match = facility_shape and zone_shape
    if not facility_shape:
        mismatches.append("Facility telemetry shape differs between runs.")
    if not zone_shape:
        mismatches.append("Zone telemetry shape differs between runs.")
    warnings_match = (
        first.get("warning_count") == second.get("warning_count")
    )
    if not warnings_match:
        mismatches.append("EnergyPlus warning count differs between runs.")

    first_energy = first.get("total_facility_electricity_kwh")
    second_energy = second.get("total_facility_electricity_kwh")
    energy_difference = _difference(first_energy, second_energy)
    relative_difference = None
    if energy_difference is not None:
        denominator = abs(float(first_energy))
        relative_difference = (
            energy_difference / denominator * 100
            if denominator else (0.0 if energy_difference == 0 else None)
        )
    peak_difference = _difference(
        first.get("peak_facility_demand_kw"),
        second.get("peak_facility_demand_kw"),
    )
    _metric_match(
        first_energy,
        second_energy,
        tolerance,
        "Total facility electricity",
        mismatches,
    )
    _metric_match(
        first.get("peak_facility_demand_kw"),
        second.get("peak_facility_demand_kw"),
        tolerance,
        "Peak facility demand",
        mismatches,
    )
    _metric_match(
        first.get("thermostat_adherence_percent"),
        second.get("thermostat_adherence_percent"),
        tolerance,
        "Thermostat adherence",
        mismatches,
    )
    _metric_match(
        first.get("temperature_compliance_percent"),
        second.get("temperature_compliance_percent"),
        tolerance,
        "Temperature compliance",
        mismatches,
    )
    _metric_match(
        first.get("pmv_compliance_percent"),
        second.get("pmv_compliance_percent"),
        tolerance,
        "PMV compliance",
        mismatches,
    )
    return BaselineReproducibilityReport(
        reproducible=not mismatches,
        exact_input_match=exact_input_match,
        energy_absolute_difference_kwh=energy_difference,
        energy_relative_difference_percent=relative_difference,
        peak_demand_difference_kw=peak_difference,
        telemetry_shape_match=telemetry_shape_match,
        warnings_match=warnings_match,
        mismatches=tuple(mismatches),
        first_run_id=first_result.run_id,
        second_run_id=second_result.run_id,
        tolerance=tolerance,
    )


__all__ = [
    "BaselineReproducibilityReport",
    "compare_baseline_runs",
]
