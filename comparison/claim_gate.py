"""Deterministic, non-marketing Phase 10 result-claim gate."""

from .schemas import ClaimGateResult


def evaluate_claim_gate(
    *,
    compatibility_passed: bool,
    controlled_run_complete: bool,
    telemetry_alignment_passed: bool,
    energy_reduction_kwh: float | None,
    energy_reduction_percent: float | None,
    comfort_gate_passed: bool,
    emergency_comfort_breach: bool,
    severe_count: int,
    fatal_count: int,
    control_injection_verified: bool,
    safety_supervisor_enabled: bool,
) -> ClaimGateResult:
    invalid_reasons: list[str] = []
    if not compatibility_passed:
        invalid_reasons.append("Run compatibility did not pass.")
    if not control_injection_verified:
        invalid_reasons.append("Control injection was not verified.")
    if not safety_supervisor_enabled:
        invalid_reasons.append("The Phase 9 safety supervisor was not enabled.")
    if severe_count:
        invalid_reasons.append(f"Controlled run severe count is {severe_count}.")
    if fatal_count:
        invalid_reasons.append(f"Controlled run fatal count is {fatal_count}.")
    if invalid_reasons:
        return ClaimGateResult(
            claim_status="comparison_invalid",
            eligible_to_claim_savings=False,
            reasons=invalid_reasons,
            warnings=[],
            approved_statement=(
                "No official savings claim is permitted because the comparison "
                "failed one or more required validity checks."
            ),
        )
    if not controlled_run_complete or not telemetry_alignment_passed:
        reasons = []
        if not controlled_run_complete:
            reasons.append("The controlled simulation horizon is incomplete.")
        if not telemetry_alignment_passed:
            reasons.append("Baseline and controlled telemetry are not fully aligned.")
        return ClaimGateResult(
            claim_status="comparison_incomplete",
            eligible_to_claim_savings=False,
            reasons=reasons,
            warnings=[],
            approved_statement=(
                "No official savings claim is permitted because the comparison "
                "horizon or telemetry alignment is incomplete."
            ),
        )
    if energy_reduction_kwh is None or energy_reduction_percent is None:
        return ClaimGateResult(
            claim_status="comparison_incomplete",
            eligible_to_claim_savings=False,
            reasons=["Energy reduction could not be calculated."],
            warnings=[],
            approved_statement=(
                "No official savings claim is permitted because comparable "
                "electricity totals are unavailable."
            ),
        )
    if energy_reduction_kwh < 0:
        return ClaimGateResult(
            claim_status="negative_energy_savings",
            eligible_to_claim_savings=False,
            reasons=["Controlled energy exceeded baseline energy."],
            warnings=[],
            approved_statement=(
                f"The controlled EnergyPlus run used "
                f"{abs(energy_reduction_kwh):.3f} kWh more electricity than "
                "the compatible fixed-schedule baseline; no savings are claimed."
            ),
        )
    if energy_reduction_kwh <= 0:
        return ClaimGateResult(
            claim_status="comfort_maintained_no_energy_savings",
            eligible_to_claim_savings=False,
            reasons=["No positive facility-electricity reduction was measured."],
            warnings=[],
            approved_statement=(
                "Comfort was evaluated on compatible EnergyPlus runs, but no "
                "positive facility-electricity savings were measured."
            ),
        )
    if not comfort_gate_passed or emergency_comfort_breach:
        reasons = []
        if not comfort_gate_passed:
            reasons.append("The configured occupied comfort gate did not pass.")
        if emergency_comfort_breach:
            reasons.append("An emergency comfort breach occurred.")
        return ClaimGateResult(
            claim_status="energy_reduced_comfort_not_maintained",
            eligible_to_claim_savings=False,
            reasons=reasons,
            warnings=[],
            approved_statement=(
                f"The compatible EnergyPlus runs measured "
                f"{energy_reduction_percent:.3f}% lower facility electricity, "
                "but comfort was not maintained, so no savings claim is approved."
            ),
        )
    return ClaimGateResult(
        claim_status="validated_positive_savings",
        eligible_to_claim_savings=True,
        reasons=[
            "Compatibility, full-horizon alignment, comfort, runtime, actuator, "
            "and deterministic safety checks passed."
        ],
        warnings=[],
        approved_statement=(
            f"Under the documented compatible EnergyPlus experiment, the "
            f"safety-supervised controlled run reduced facility electricity by "
            f"{energy_reduction_kwh:.3f} kWh ({energy_reduction_percent:.3f}%) "
            "while meeting the configured occupied comfort gate."
        ),
    )


__all__ = ["evaluate_claim_gate"]
