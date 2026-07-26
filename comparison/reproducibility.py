"""Deterministic comparison-output reproducibility checks."""

from typing import Any

from .schemas import ReproducibilityReport
from .settings import COMPARISON_SETTINGS, ComparisonSettings


def compare_repeated_results(
    first: dict[str, Any],
    second: dict[str, Any],
    *,
    first_identity: dict[str, Any],
    second_identity: dict[str, Any],
    first_action_count: int,
    second_action_count: int,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> ReproducibilityReport:
    tolerance = settings.reproducibility_tolerance

    def close(name: str) -> bool:
        left = first.get(name)
        right = second.get(name)
        return (
            isinstance(left, (int, float))
            and isinstance(right, (int, float))
            and abs(float(left) - float(right)) <= tolerance
        )

    model_match = (
        first_identity.get("derived_model_hash")
        == second_identity.get("derived_model_hash")
    )
    weather_match = (
        first_identity.get("weather_hash")
        == second_identity.get("weather_hash")
    )
    shape_match = (
        first_identity.get("interval_count")
        == second_identity.get("interval_count")
    )
    energy_match = close("controlled_energy_kwh")
    peak_match = close("controlled_peak_demand_kw")
    comfort_match = close("controlled_comfort_percent")
    action_match = first_action_count == second_action_count
    status_match = first.get("claim_status") == second.get("claim_status")
    checks = {
        "model hashes": model_match,
        "weather hashes": weather_match,
        "telemetry shape": shape_match,
        "energy total": energy_match,
        "peak demand": peak_match,
        "comfort metric": comfort_match,
        "action count": action_match,
        "comparison status": status_match,
    }
    return ReproducibilityReport(
        reproducible=all(checks.values()),
        mode=str(first.get("comparison_mode", "reproducible_policy")),
        first_comparison_id=str(first.get("comparison_id", "")),
        second_comparison_id=str(second.get("comparison_id", "")),
        model_hashes_match=model_match,
        weather_hashes_match=weather_match,
        telemetry_shape_match=shape_match,
        energy_within_tolerance=energy_match,
        peak_demand_within_tolerance=peak_match,
        comfort_within_tolerance=comfort_match,
        action_counts_match=action_match,
        comparison_status_match=status_match,
        mismatches=[name for name, passed in checks.items() if not passed],
        limitations=[],
        tolerance=tolerance,
    )


__all__ = ["compare_repeated_results"]
