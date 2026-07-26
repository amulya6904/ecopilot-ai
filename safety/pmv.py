"""PMV/PPD rules used only when genuine EnergyPlus values are available."""

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .schemas import SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


def evaluate_pmv_rules(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> list[SafetyRuleResult]:
    if state.pmv is None:
        return [
            SafetyRuleResult(
                rule_id="PMV_UNAVAILABLE_USING_TEMPERATURE_PROXY",
                passed=False,
                severity="warning",
                message=(
                    "PMV is genuinely unavailable; occupied-temperature proxy "
                    "rules are used without fabricating PMV."
                ),
                observed_value=None,
                threshold=[settings.pmv_min, settings.pmv_max],
                unit="PMV",
                action="none",
            )
        ]
    delta = candidate.requested_value_c - candidate.current_value_c
    too_hot = state.pmv > settings.pmv_max
    too_cold = state.pmv < settings.pmv_min
    rules = [
        SafetyRuleResult(
            rule_id="PMV_HOT_LIMIT",
            passed=not (state.occupied and too_hot and delta > 0),
            severity=(
                "info"
                if not (state.occupied and too_hot and delta > 0)
                else "critical"
            ),
            message="Do not relax cooling while occupied PMV is above its limit.",
            observed_value=state.pmv,
            threshold=settings.pmv_max,
            unit="PMV",
            action=(
                "none"
                if not (state.occupied and too_hot and delta > 0)
                else "fallback"
            ),
        ),
        SafetyRuleResult(
            rule_id="PMV_COLD_LIMIT",
            passed=not (state.occupied and too_cold and delta < 0),
            severity=(
                "info"
                if not (state.occupied and too_cold and delta < 0)
                else "critical"
            ),
            message="Do not increase cooling while occupied PMV is below its limit.",
            observed_value=state.pmv,
            threshold=settings.pmv_min,
            unit="PMV",
            action=(
                "none"
                if not (state.occupied and too_cold and delta < 0)
                else "fallback"
            ),
        ),
    ]
    if state.ppd_percent is not None:
        warning = state.ppd_percent > settings.ppd_warning_percent
        rules.append(
            SafetyRuleResult(
                rule_id="PPD_WARNING_ACTIVE",
                passed=not warning,
                severity="warning" if warning else "info",
                message="PPD exceeds the prototype warning threshold.",
                observed_value=state.ppd_percent,
                threshold=settings.ppd_warning_percent,
                unit="%",
                action="none",
            )
        )
    return rules


__all__ = ["evaluate_pmv_rules"]
