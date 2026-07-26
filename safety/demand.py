"""Prototype demand warning and critical supervisory rules."""

from energyplus.runtime_control.schemas import ExecutableActionCandidate

from .schemas import DemandAssessment, SafetyRuleResult, SafetyStateSnapshot
from .settings import SAFETY_SETTINGS, SafetySettings


def evaluate_demand(
    state: SafetyStateSnapshot,
    candidate: ExecutableActionCandidate,
    settings: SafetySettings = SAFETY_SETTINGS,
) -> DemandAssessment:
    demand = state.facility_demand_kw
    delta = candidate.requested_value_c - candidate.current_value_c
    if demand is None:
        return DemandAssessment(
            status="unavailable",
            demand_kw=None,
            rules=[
                SafetyRuleResult(
                    rule_id="DEMAND_DATA_UNAVAILABLE",
                    passed=False,
                    severity="warning",
                    message=(
                        "Facility demand is unavailable; no precise demand "
                        "effect is claimed."
                    ),
                    observed_value=None,
                    threshold=settings.demand_warning_kw,
                    unit="kW",
                    action="none",
                )
            ],
        )
    status = (
        "critical"
        if demand >= settings.demand_critical_kw
        else "warning"
        if demand >= settings.demand_warning_kw
        else "normal"
    )
    rules: list[SafetyRuleResult] = []
    if status == "warning":
        rules.append(
            SafetyRuleResult(
                rule_id="DEMAND_WARNING_ACTIVE",
                passed=False,
                severity="warning",
                message=(
                    "Prototype demand warning is active; only neutral or "
                    "demand-reducing direction is allowed with comfort headroom."
                ),
                observed_value=demand,
                threshold=settings.demand_warning_kw,
                unit="kW",
                action="none",
            )
        )
    if status == "critical":
        rules.append(
            SafetyRuleResult(
                rule_id="DEMAND_CRITICAL_ACTIVE",
                passed=False,
                severity="critical",
                message="Prototype critical facility demand threshold is active.",
                observed_value=demand,
                threshold=settings.demand_critical_kw,
                unit="kW",
                action="none",
            )
        )
    demand_increasing = status in {"warning", "critical"} and delta < 0
    rules.append(
        SafetyRuleResult(
            rule_id="DEMAND_INCREASING_ACTION_REJECTED",
            passed=not demand_increasing,
            severity="critical" if demand_increasing else "info",
            message=(
                "Lowering a cooling setpoint during elevated demand is rejected "
                "as demand-increasing direction."
            ),
            observed_value={"demand_kw": demand, "delta_c": delta},
            threshold={
                "warning_kw": settings.demand_warning_kw,
                "critical_kw": settings.demand_critical_kw,
            },
            unit="kW",
            action="reject" if demand_increasing else "none",
        )
    )
    return DemandAssessment(status=status, demand_kw=demand, rules=rules)


__all__ = ["evaluate_demand"]
