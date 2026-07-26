"""Occupancy-aware genuine PMV or explicit temperature-proxy comfort logic."""

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .pmv import evaluate_pmv_rules
from .schemas import ComfortEvaluation, SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


def evaluate_comfort(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> ComfortEvaluation:
    if state.pmv is not None:
        rules = evaluate_pmv_rules(state, candidate, settings)
        status = (
            "unoccupied"
            if not state.occupied
            else "too_hot"
            if state.pmv > settings.pmv_max
            else "too_cold"
            if state.pmv < settings.pmv_min
            else "comfortable"
        )
        return ComfortEvaluation(
            comfort_method="pmv_ppd",
            pmv_available=True,
            current_status=status,
            safe_headroom_c=max(
                0.0,
                settings.maximum_setpoint_change_c
                if status in {"comfortable", "unoccupied"}
                else 0.0,
            ),
            risk_level=(
                "high"
                if status in {"too_hot", "too_cold"}
                else "low"
            ),
            proposed_action_effect=(
                "Evaluated against genuine PMV direction and PPD."
            ),
            rules=rules,
        )

    warning = evaluate_pmv_rules(state, candidate, settings)
    temperature = state.indoor_temperature_c
    if not state.occupied:
        status = "unoccupied"
        lower = settings.unoccupied_temperature_min_c
        upper = settings.unoccupied_temperature_max_c
    else:
        lower = settings.occupied_temperature_min_c
        upper = settings.occupied_temperature_max_c
        status = (
            "unknown"
            if temperature is None
            else "too_hot"
            if temperature > upper
            else "too_cold"
            if temperature < lower
            else "comfortable"
        )
    delta = candidate.requested_value_c - candidate.current_value_c
    worsens_hot = state.occupied and status == "too_hot" and delta > 0
    worsens_cold = state.occupied and status == "too_cold" and delta < 0
    rule = SafetyRuleResult(
        rule_id="TEMPERATURE_PROXY_DIRECTION_RISK",
        passed=not (worsens_hot or worsens_cold),
        severity="critical" if worsens_hot or worsens_cold else "info",
        message=(
            "Setpoint direction must not worsen an occupied temperature violation."
        ),
        observed_value={
            "temperature_c": temperature,
            "requested_delta_c": delta,
        },
        threshold=[lower, upper],
        unit="C",
        action="fallback" if worsens_hot or worsens_cold else "none",
    )
    if temperature is None:
        headroom = 0.0
    elif delta >= 0:
        headroom = max(0.0, upper - temperature)
    else:
        headroom = max(0.0, temperature - lower)
    return ComfortEvaluation(
        comfort_method="occupied_temperature_proxy",
        pmv_available=False,
        current_status=status,
        safe_headroom_c=headroom,
        risk_level=(
            "critical"
            if temperature is not None
            and not (
                settings.emergency_temperature_min_c
                <= temperature
                <= settings.emergency_temperature_max_c
            )
            else "high"
            if status in {"too_hot", "too_cold", "unknown"}
            else "medium"
        ),
        proposed_action_effect=(
            "Direction checked against occupied temperature headroom; PMV "
            "was not estimated."
        ),
        rules=warning + [rule],
    )


__all__ = ["evaluate_comfort"]
