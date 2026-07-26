"""Measured-result-only Phase 10 executive summary generation."""

from typing import Any


def build_executive_summary(
    final_summary: dict[str, Any],
    *,
    compatibility_status: str,
    baseline_run_id: str,
    controlled_run_id: str,
    control_mode: str,
) -> str:
    eligibility = final_summary["eligible_to_claim_savings"]
    return "\n".join([
        "# EcoPilot AI Phase 10 executive summary",
        "",
        "## Result",
        "",
        final_summary["exact_approved_statement"],
        "",
        "## Experiment identity",
        "",
        f"- Baseline run: `{baseline_run_id}`",
        f"- Controlled run: `{controlled_run_id}`",
        f"- Control mode: `{control_mode}`",
        f"- Compatibility: `{compatibility_status}`",
        "- Backend/source: EnergyPlus / EnergyPlus",
        "- Safety authority: deterministic Phase 9 supervisor",
        "",
        "## Measured metrics",
        "",
        f"- Baseline facility electricity: {final_summary.get('baseline_energy_kwh')} kWh",
        f"- Controlled facility electricity: {final_summary.get('controlled_energy_kwh')} kWh",
        f"- Energy reduction: {final_summary.get('energy_reduction_kwh')} kWh",
        f"- Energy reduction percentage: {final_summary.get('energy_reduction_percent')}%",
        f"- Baseline peak demand: {final_summary.get('baseline_peak_demand_kw')} kW",
        f"- Controlled peak demand: {final_summary.get('controlled_peak_demand_kw')} kW",
        f"- Baseline occupied comfort: {final_summary.get('baseline_comfort_percent')}%",
        f"- Controlled occupied comfort: {final_summary.get('controlled_comfort_percent')}%",
        f"- Severe/fatal errors: {final_summary.get('severe_count')}/{final_summary.get('fatal_count')}",
        "",
        "## Claim decision",
        "",
        f"- Status: `{final_summary['claim_status']}`",
        f"- Eligible to claim savings: `{str(eligibility).lower()}`",
        "",
        "Cost and carbon are derived from the documented Phase 10 tariff and "
        "grid-intensity assumptions; they are not raw EnergyPlus outputs.",
    ]) + "\n"


__all__ = ["build_executive_summary"]
