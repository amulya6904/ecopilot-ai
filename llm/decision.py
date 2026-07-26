"""Compact LLM decision context and deterministic proposal assembly."""

import json
from typing import Any
import uuid

from config.settings import HVAC
from llm.schemas import (
    ComfortAssessment,
    ControlProposal,
    EffectivePeriod,
    EvidenceItem,
    ExpectedEffect,
    LLMDecision,
)
from llm.settings import LLMSettings


COMPACT_SYSTEM_PROMPT = (
    "You make one advisory HVAC decision from supplied official evidence. "
    "Return only JSON matching the separately supplied schema. Do not reveal "
    "reasoning or claim application, closed-loop control, optimization, or savings."
)

_OPTIMALITY_TERMS = ("optimal", "best", "minimum energy")


def _tool_data(history: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for event in history:
        data = event.get("response", {}).get("data")
        if event.get("tool") == name and event.get("success") and isinstance(data, dict):
            return data
    raise ValueError(f"Required MCP evidence is missing: {name}.")


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} is not numeric.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not numeric.") from exc


def _evidence_values(history: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = _tool_data(history, "get_official_baseline_summary")
    facility = _tool_data(history, "get_facility_summary")
    zone_data = _tool_data(history, "list_zones")
    comfort = _tool_data(history, "get_comfort_summary")
    adherence = _tool_data(history, "get_thermostat_adherence")
    frozen_policy = adherence.get("frozen_policy")
    if not isinstance(frozen_policy, dict):
        raise ValueError("Thermostat evidence has no frozen policy.")
    cooling = frozen_policy.get("cooling_setpoint_c")
    if not isinstance(cooling, dict):
        raise ValueError("Thermostat evidence has no cooling policy.")
    eligible_zones = [
        {
            "energyplus_zone_name": item.get("energyplus_zone_name"),
            "display_zone_name": item.get("display_zone_name"),
        }
        for item in zone_data.get("zones", [])
        if (
            isinstance(item, dict)
            and item.get("role") != "plenum"
            and item.get("included_in_comfort") is True
            and isinstance(item.get("energyplus_zone_name"), str)
            and isinstance(item.get("display_zone_name"), str)
        )
    ]
    if not eligible_zones:
        raise ValueError("MCP evidence contains no eligible occupied non-plenum zone.")
    return {
        "baseline": baseline,
        "facility": facility,
        "zones": zone_data,
        "comfort": comfort,
        "adherence": adherence,
        "eligible_zones": eligible_zones,
        "current_setpoint_c": _number(
            cooling.get("occupied"),
            "Occupied cooling setpoint",
        ),
        "temperature_compliance_percent": _number(
            comfort.get("temperature_compliance_percent"),
            "Temperature compliance",
        ),
        "facility_peak_demand_kw": _number(
            facility.get("peak_facility_demand_kw"),
            "Facility peak demand",
        ),
        "pmv_available": bool(comfort.get("pmv_available")),
    }


def build_final_decision_prompt(
    history: list[dict[str, Any]],
    analysis_focus: str = "",
) -> str:
    """Build the only evidence view sent to the final model request."""
    values = _evidence_values(history)
    compact = {
        "eligible_occupied_non_plenum_zones": values["eligible_zones"],
        "current_setpoint_c": values["current_setpoint_c"],
        "allowed_setpoint_range_c": [
            HVAC.minimum_setpoint_c,
            HVAC.maximum_setpoint_c,
        ],
        "maximum_permitted_delta_c": HVAC.maximum_setpoint_change_c,
        "temperature_compliance_percent": values["temperature_compliance_percent"],
        "facility_peak_demand_kw": values["facility_peak_demand_kw"],
        "pmv_available": values["pmv_available"],
        "analysis_focus": analysis_focus.strip()[:300] or "none",
        "advisory_only_prohibition": (
            "Choose one advisory decision only. Do not claim application, "
            "closed-loop control, optimization, or savings."
        ),
        "hold_policy": (
            "If proposed_setpoint_c equals current_setpoint_c, explain risk, "
            "uncertainty, or insufficient evidence. Never call the current value "
            "optimal, best, or minimum-energy without a real candidate comparison."
        ),
    }
    return (
        "Choose the eligible zone, proposed cooling setpoint, objective, confidence, "
        "and a concise reason. Confidence must be a decimal from 0 to 1, not a percentage. "
        "Return only the JSON object constrained by the separately supplied schema; "
        "do not output model reasoning.\n"
        + json.dumps(compact, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


def build_final_decision_messages(
    history: list[dict[str, Any]],
    analysis_focus: str = "",
) -> list[dict[str, str]]:
    """Return exactly the compact system and compact evidence messages."""
    return [
        {"role": "system", "content": COMPACT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_final_decision_prompt(history, analysis_focus),
        },
    ]


def assemble_control_proposal(
    decision: LLMDecision,
    history: list[dict[str, Any]],
    settings: LLMSettings,
) -> ControlProposal:
    """Build every factual and safety-controlled proposal field in Python."""
    values = _evidence_values(history)
    matching_zone = next(
        (
            item for item in values["eligible_zones"]
            if item["energyplus_zone_name"] == decision.energyplus_zone_name
        ),
        None,
    )
    if matching_zone is None:
        raise ValueError("LLM decision selected a zone that is not eligible.")

    current = values["current_setpoint_c"]
    delta = decision.proposed_setpoint_c - current
    comfort = values["comfort"]
    baseline = values["baseline"]
    hours = values["adherence"].get("frozen_policy", {}).get("occupied_hours")
    if not (
        isinstance(hours, list)
        and len(hours) == 2
        and all(isinstance(value, int) for value in hours)
    ):
        hours = [9, 18]

    pmv_available = values["pmv_available"]
    pmv_compliance = (
        _number(comfort.get("pmv_compliance_percent"), "PMV compliance")
        if pmv_available and comfort.get("pmv_compliance_percent") is not None
        else None
    )
    limitations = [
        "A future matched simulation and deterministic safety review are required."
    ]
    if not pmv_available:
        limitations.insert(
            0,
            str(comfort.get("pmv_unavailable_reason") or "PMV is unavailable."),
        )
    temperature_compliance = values["temperature_compliance_percent"]
    risk_level = (
        "high"
        if temperature_compliance < 90
        else "medium"
        if not pmv_available or abs(delta) > 1
        else "low"
    )
    confidence_limit = 1.0
    if temperature_compliance < 90:
        confidence_limit = min(confidence_limit, 0.5)
    if not pmv_available:
        confidence_limit = min(confidence_limit, 0.45)
    occupancy_source = str(comfort.get("occupancy_source") or "unavailable")
    if occupancy_source.casefold() in {"unavailable", "unknown", "none"}:
        confidence_limit = min(confidence_limit, 0.35)
    confidence = min(decision.confidence, confidence_limit)
    is_hold = abs(delta) <= 1e-6
    reason = decision.reason.strip()
    if is_hold and (
        any(term in reason.casefold() for term in _OPTIMALITY_TERMS)
        or not any(
            term in reason.casefold()
            for term in ("risk", "uncertain", "insufficient", "unavailable", "evidence")
        )
    ):
        reason = (
            "Hold the current setpoint because low comfort compliance, unavailable "
            "PMV, or incomplete telemetry leaves insufficient evidence for a safe change."
        )

    total_electricity = _number(
        baseline.get("total_facility_electricity_kwh"),
        "Official facility electricity",
    )
    evidence = [
        EvidenceItem(
            source_tool="get_official_baseline_summary",
            metric="total_facility_electricity_kwh",
            value=total_electricity,
            unit="kWh",
            observation="Official fixed-schedule EnergyPlus baseline total.",
        ),
        EvidenceItem(
            source_tool="get_facility_summary",
            metric="peak_facility_demand_kw",
            value=values["facility_peak_demand_kw"],
            unit="kW",
            observation="Official EnergyPlus baseline peak facility demand.",
        ),
        EvidenceItem(
            source_tool="list_zones",
            metric="eligible_occupied_non_plenum_zone",
            value=decision.energyplus_zone_name,
            unit="zone",
            observation="Selected zone is occupied, non-plenum, and included in comfort.",
        ),
        EvidenceItem(
            source_tool="get_thermostat_adherence",
            metric="current_cooling_setpoint_c",
            value=current,
            unit="degC",
            observation="Occupied cooling setpoint from the frozen thermostat policy.",
        ),
        EvidenceItem(
            source_tool="get_comfort_summary",
            metric="temperature_compliance_percent",
            value=temperature_compliance,
            unit="percent",
            observation="Occupied-zone temperature compliance from official evidence.",
        ),
    ]
    return ControlProposal(
        proposal_id=f"phase7-{uuid.uuid4().hex}",
        decision_type=(
            "hold_current_setpoint"
            if is_hold
            else "cooling_setpoint_advisory"
        ),
        energyplus_zone_name=decision.energyplus_zone_name,
        display_zone_name=matching_zone["display_zone_name"],
        current_setpoint_c=current,
        proposed_setpoint_c=decision.proposed_setpoint_c,
        setpoint_change_c=delta,
        effective_period=EffectivePeriod(
            start_hour=hours[0],
            end_hour=hours[1],
            description="Future occupied period; advisory only.",
        ),
        objective=decision.objective,
        evidence=evidence,
        comfort_assessment=ComfortAssessment(
            occupancy_source=occupancy_source,
            temperature_compliance_percent=temperature_compliance,
            pmv_available=pmv_available,
            pmv_compliance_percent=pmv_compliance,
            risk_level=risk_level,
            limitations=limitations,
        ),
        expected_effect=ExpectedEffect(
            energy="Potential effect only; no matched controlled simulation was run.",
            comfort="Setpoint impact requires independent safety review.",
            demand="Potential demand effect is not a measured savings result.",
            uncertainty="No action was applied and no savings comparison was performed.",
        ),
        confidence=confidence,
        reason=reason,
        advisory_only=True,
        requires_safety_review=True,
        applied_to_energyplus=False,
        closed_loop=False,
        optimized_result=False,
        savings_result=False,
    )


def build_timeout_fallback_decision(
    history: list[dict[str, Any]],
) -> LLMDecision:
    """Choose a conservative, separately classified fallback from MCP evidence."""
    values = _evidence_values(history)
    current = values["current_setpoint_c"]
    safe_to_adjust = (
        HVAC.minimum_setpoint_c <= current <= HVAC.maximum_setpoint_c
        and values["temperature_compliance_percent"] >= 90
    )
    proposed = current
    if safe_to_adjust:
        proposed = min(
            current + 0.5,
            current + HVAC.maximum_setpoint_change_c,
            HVAC.maximum_setpoint_c,
        )
    return LLMDecision(
        energyplus_zone_name=values["eligible_zones"][0]["energyplus_zone_name"],
        proposed_setpoint_c=proposed,
        objective=("reduce_energy" if proposed > current else "maintain_comfort"),
        confidence=0.35,
        reason=(
            "Conservative timeout fallback limited to a 0.5 C advisory increase."
            if proposed > current
            else "Timeout fallback keeps the current setpoint because evidence is insufficient."
        ),
    )


__all__ = [
    "COMPACT_SYSTEM_PROMPT",
    "assemble_control_proposal",
    "build_final_decision_messages",
    "build_final_decision_prompt",
    "build_timeout_fallback_decision",
]
