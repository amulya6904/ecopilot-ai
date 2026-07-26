"""Deterministic proposal checks independent of model reasoning."""

from typing import Any

from config.settings import HVAC
from llm.mcp_client import MODEL_TOOL_ALLOWLIST
from llm.schemas import ControlProposal, ProposalValidationResult
from llm.settings import LLMSettings


VALIDATOR_VERSION = "phase7-validator-v2"
UNSUPPORTED_OPTIMALITY_CLAIM = "UNSUPPORTED_OPTIMALITY_CLAIM"
LOW_COMFORT_CONFIDENCE = "LOW_COMFORT_CONFIDENCE"
_OPTIMALITY_TERMS = ("optimal", "best", "minimum energy")


def _tool_data(history: list[dict[str, Any]], name: str) -> list[Any]:
    return [
        event.get("response", {}).get("data")
        for event in history if event.get("tool") == name and event.get("success")
    ]


def validate_proposal(
    proposal: ControlProposal,
    tool_history: list[dict[str, Any]],
    settings: LLMSettings,
) -> ProposalValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    called = {event.get("tool") for event in tool_history if event.get("success")}
    zones: list[dict[str, Any]] = []
    for data in _tool_data(tool_history, "list_zones"):
        zones.extend(data.get("zones", []) if isinstance(data, dict) else [])
    zone = next(
        (item for item in zones if item.get("energyplus_zone_name") == proposal.energyplus_zone_name),
        None,
    )
    if zone is None:
        errors.append("Technical zone was not confirmed by list_zones.")
    else:
        if zone.get("display_zone_name") != proposal.display_zone_name:
            errors.append("Display alias does not match the technical zone.")
        if zone.get("role") == "plenum" or zone.get("included_in_comfort") is not True:
            errors.append("Proposal zone must be occupied, non-plenum, and included in comfort.")
    if not HVAC.minimum_setpoint_c <= proposal.proposed_setpoint_c <= HVAC.maximum_setpoint_c:
        errors.append("Proposed setpoint is outside configured HVAC bounds.")
    if abs(proposal.setpoint_change_c) > HVAC.maximum_setpoint_change_c:
        errors.append("Setpoint change exceeds configured maximum.")
    if proposal.proposed_setpoint_c <= proposal.current_setpoint_c - HVAC.maximum_setpoint_change_c - 1e-6:
        errors.append("Cooling proposal change is unsafe.")
    adherence = _tool_data(tool_history, "get_thermostat_adherence")
    heating = None
    for data in adherence:
        try:
            heating = float(data["frozen_policy"]["heating_setpoint_c"]["occupied"])
        except (KeyError, TypeError, ValueError):
            pass
    if heating is not None and proposal.proposed_setpoint_c < heating + settings.minimum_deadband_c:
        errors.append("Proposed cooling setpoint violates the heating deadband.")
    current_evidence = [
        item for item in proposal.evidence
        if item.metric == "current_cooling_setpoint_c"
        and item.source_tool in {"get_zone_telemetry", "get_thermostat_adherence"}
        and isinstance(item.value, (int, float))
    ]
    if not current_evidence or all(abs(float(item.value) - proposal.current_setpoint_c) > 1e-6 for item in current_evidence):
        errors.append("Current cooling setpoint is not supported by matching MCP evidence.")
    for evidence in proposal.evidence:
        if evidence.source_tool not in MODEL_TOOL_ALLOWLIST:
            errors.append(f"Evidence uses a non-allowlisted tool: {evidence.source_tool}.")
        elif evidence.source_tool not in called:
            errors.append(f"Evidence cites a tool that was not called: {evidence.source_tool}.")
    required_evidence_sources = {
        "get_official_baseline_summary", "get_facility_summary",
        "get_comfort_summary", "get_thermostat_adherence",
    }
    cited = {item.source_tool for item in proposal.evidence}
    missing_sources = required_evidence_sources - cited
    if missing_sources:
        errors.append(
            "Proposal evidence is missing required MCP sources: "
            f"{sorted(missing_sources)}."
        )
    comfort_data = next(iter(_tool_data(tool_history, "get_comfort_summary")), None)
    if isinstance(comfort_data, dict):
        actual_pmv = bool(comfort_data.get("pmv_available"))
        if proposal.comfort_assessment.pmv_available != actual_pmv:
            errors.append("PMV availability claim conflicts with MCP comfort data.")
        if not actual_pmv and proposal.comfort_assessment.pmv_compliance_percent is not None:
            errors.append("PMV compliance must be null when PMV is unavailable.")
        if proposal.comfort_assessment.occupancy_source != comfort_data.get("occupancy_source"):
            errors.append("Occupancy source conflicts with MCP comfort data.")
        actual_temp = comfort_data.get("temperature_compliance_percent")
        if actual_temp is not None and abs(proposal.comfort_assessment.temperature_compliance_percent - float(actual_temp)) > 1e-6:
            errors.append("Temperature compliance conflicts with MCP comfort data.")
        low_comfort_confidence = (
            actual_temp is None
            or float(actual_temp) < 90
            or not actual_pmv
            or str(comfort_data.get("occupancy_source") or "").casefold()
            in {"", "unavailable", "unknown", "none"}
        )
        if low_comfort_confidence:
            warnings.append(
                f"{LOW_COMFORT_CONFIDENCE}: Comfort certainty is reduced because "
                "temperature compliance is low, PMV is unavailable, or telemetry "
                "is incomplete."
            )
            confidence_cap = (
                0.35
                if str(comfort_data.get("occupancy_source") or "").casefold()
                in {"", "unavailable", "unknown", "none"}
                else 0.45
                if not actual_pmv
                else 0.5
            )
            if proposal.confidence > confidence_cap + 1e-6:
                errors.append(
                    f"{LOW_COMFORT_CONFIDENCE}: Confidence exceeds the deterministic "
                    f"{confidence_cap:.2f} comfort-evidence cap."
                )
    else:
        errors.append("Comfort summary was not retrieved.")
    is_hold = abs(proposal.setpoint_change_c) <= 1e-6
    if is_hold and proposal.decision_type != "hold_current_setpoint":
        errors.append(
            "A zero-delta proposal must use decision_type "
            "'hold_current_setpoint'."
        )
    if not is_hold and proposal.decision_type == "hold_current_setpoint":
        errors.append("A hold decision cannot request a setpoint change.")
    unsupported_claim = any(
        term in proposal.reason.casefold() for term in _OPTIMALITY_TERMS
    )
    if unsupported_claim:
        errors.append(
            f"{UNSUPPORTED_OPTIMALITY_CLAIM}: Optimality or minimum-energy wording "
            "requires a real candidate comparison."
        )
    if is_hold and not any(
        term in proposal.reason.casefold()
        for term in ("risk", "uncertain", "insufficient", "unavailable", "evidence")
    ):
        errors.append(
            "A hold reason must explain risk, uncertainty, or insufficient evidence."
        )
    if proposal.setpoint_change_c <= 0:
        warnings.append("Proposal does not raise the cooling setpoint; energy-reduction benefit is uncertain.")
    if not {"get_official_baseline_summary", "get_facility_summary", "list_zones", "get_comfort_summary"}.issubset(called):
        errors.append("Required baseline, facility, zone, and comfort evidence tools were not all called.")
    return ProposalValidationResult(
        valid=not errors,
        validation_errors=errors,
        validation_warnings=warnings,
        normalized_proposal=proposal if not errors else None,
        validator_version=VALIDATOR_VERSION,
    )


__all__ = [
    "LOW_COMFORT_CONFIDENCE",
    "UNSUPPORTED_OPTIMALITY_CLAIM",
    "VALIDATOR_VERSION",
    "validate_proposal",
]
