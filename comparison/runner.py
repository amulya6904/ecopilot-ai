"""Full controlled evaluation and official Phase 10 comparison orchestration."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from energyplus.adapter.error_parser import parse_energyplus_error_file
from energyplus.baseline.manifest import calculate_sha256
from energyplus.baseline.normalizer import normalize_energyplus_baseline_csv
from energyplus.baseline.schedule_inspector import inspect_baseline_model
from energyplus.baseline.settings import ENERGYPLUS_BASELINE
from energyplus.runtime_control.action_provider import (
    ProviderDecision,
    build_candidate,
)
from energyplus.runtime_control.runtime_runner import run_phase8_runtime

from .agent_metrics import calculate_agent_metrics
from .alignment import align_telemetry
from .artifact_loader import (
    LoadedRun,
    load_baseline_artifact,
    load_controlled_artifact,
    stable_json_hash,
)
from .artifacts import (
    new_comparison_id,
    write_comparison_bundle,
    write_csv,
    write_json,
)
from .carbon import calculate_carbon_metrics
from .claim_gate import evaluate_claim_gate
from .comfort import calculate_comfort_metrics
from .compatibility import compare_run_compatibility
from .cost import calculate_cost_metrics
from .demand import calculate_demand_metrics
from .energy import calculate_energy_metrics
from .executive_summary import build_executive_summary
from .normalization import (
    ACTION_COLUMNS,
    normalize_actions,
    normalize_facility,
    normalize_zone,
)
from .reliability import calculate_reliability_metrics
from .safety_metrics import calculate_safety_metrics
from .schemas import ComparisonSummary, ReproducibilityReport
from .settings import COMPARISON_SETTINGS, ComparisonSettings


CONTROLLED_CLASSIFICATION = (
    "official_energyplus_safety_supervised_controlled_evaluation"
)


@dataclass(frozen=True)
class ControlledEvaluationResult:
    success: bool
    artifact_directory: Path
    summary: dict[str, Any]


@dataclass(frozen=True)
class ComparisonRunResult:
    success: bool
    artifact_directory: Path
    summary: dict[str, Any]


class ReproduciblePolicyProvider:
    """Hourly deterministic demand-aware policy; Phase 9 remains final authority."""

    def __init__(
        self,
        settings: ComparisonSettings,
        *,
        advisory_target_c: float | None = None,
    ) -> None:
        self.settings = settings
        self.complete = False
        self._decision_hour: tuple[int, int] | None = None
        self._active_override = False
        self._expected_target_c: float | None = None
        self.baseline_setpoint_c: float | None = None
        self.changed_setpoint_c: float | None = None
        self.override_observed = False
        self.reset_observed = False
        self.fallback_observed = False
        self._intervals_completed = 0
        self.policy_opportunities = 0
        self.policy_resets = 0
        self.advisory_target_c = advisory_target_c

    @property
    def intervals_completed(self) -> int:
        return self._intervals_completed

    def next_decision(self, telemetry, actuator):
        stamp = telemetry.simulation_timestamp
        hour_key = (stamp.timetuple().tm_yday, stamp.hour)
        if hour_key == self._decision_hour:
            return None
        self._decision_hour = hour_key
        self._intervals_completed += 1
        if self.baseline_setpoint_c is None:
            self.baseline_setpoint_c = telemetry.current_cooling_setpoint_c
        occupied = (
            telemetry.occupancy is not None and telemetry.occupancy > 0
        )
        demand = telemetry.facility_demand_kw
        temperature = telemetry.zone_temperature_c
        has_headroom = (
            temperature
            <= (
                self.settings.occupied_temperature_max_c
                - self.settings.controlled_setpoint_step_c
            )
        )
        elevated_demand = (
            demand is not None
            and self.settings.demand_warning_kw
            <= demand
            < self.settings.demand_critical_kw
        )
        final_hour = stamp.month == 12 and stamp.day == 31 and stamp.hour >= 23
        opportunity = (
            occupied and has_headroom and elevated_demand and not final_hour
        )
        if opportunity:
            baseline_occupied_c = (
                ENERGYPLUS_BASELINE.occupied_cooling_setpoint_c
            )
            deterministic_target = (
                baseline_occupied_c
                + self.settings.controlled_setpoint_step_c
            )
            target = deterministic_target
            if self.advisory_target_c is not None:
                target = min(
                    max(self.advisory_target_c, baseline_occupied_c),
                    baseline_occupied_c + 1.0,
                )
            target = min(
                max(
                    target,
                    telemetry.current_cooling_setpoint_c
                    - 1.0,
                ),
                telemetry.current_cooling_setpoint_c + 1.0,
                28.0,
            )
            self._active_override = True
            self._expected_target_c = target
            self.changed_setpoint_c = target
            self.policy_opportunities += 1
            candidate = build_candidate(
                telemetry,
                actuator,
                target,
                "reproducible_policy",
                objective="reduce_peak_demand",
                reason="phase10_deterministic_demand_and_comfort_policy",
            )
            return ProviderDecision(
                "apply",
                candidate,
                {
                    "source": "phase10_reproducible_policy",
                    "policy_version": "phase10-reproducible-policy-v1",
                    "official_evidence": "EnergyPlusRuntime:live_telemetry",
                    "occupied": occupied,
                    "indoor_temperature_c": temperature,
                    "facility_demand_kw": demand,
                    "requested_setpoint_c": target,
                    "comfort_headroom_required_c": (
                        self.settings.controlled_setpoint_step_c
                    ),
                    "advisory_target_c": self.advisory_target_c,
                },
                "phase10_policy_apply",
            )
        if self._active_override:
            self._active_override = False
            self._expected_target_c = None
            self.policy_resets += 1
            return ProviderDecision(
                "reset",
                None,
                {
                    "source": "phase10_reproducible_policy",
                    "action": "baseline_fallback_reset",
                    "occupied": occupied,
                    "indoor_temperature_c": temperature,
                    "facility_demand_kw": demand,
                },
                "phase10_policy_reset",
            )
        return None

    def observe(self, setpoint_c: float, reset_active: bool) -> None:
        if (
            not reset_active
            and self._expected_target_c is not None
            and abs(setpoint_c - self._expected_target_c) <= 0.15
        ):
            self.override_observed = True
        if reset_active:
            self.reset_observed = True


def _read_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, list) else []


def _controlled_action_summary(
    runtime_directory: Path,
    safety_directory: Path,
) -> pd.DataFrame:
    applied_path = runtime_directory / "applied_actions.csv"
    applied = (
        pd.read_csv(applied_path)
        if applied_path.is_file() and applied_path.stat().st_size
        else pd.DataFrame()
    )
    if applied.empty:
        return pd.DataFrame(columns=ACTION_COLUMNS)
    aggregated = applied.groupby("action_id", as_index=False).agg({
        "simulation_timestamp": "first",
        "requested_value": "first",
        "approved_value": "first",
        "applied_value": "first",
        "observed_setpoint_after_application": "last",
    }).rename(columns={
        "simulation_timestamp": "timestamp",
        "requested_value": "requested_setpoint_c",
        "approved_value": "approved_setpoint_c",
        "applied_value": "applied_setpoint_c",
        "observed_setpoint_after_application": "observed_setpoint_c",
    })
    decisions = pd.DataFrame(
        _read_list(safety_directory / "safety_decisions.json")
    )
    if not decisions.empty:
        aggregated = aggregated.merge(
            decisions[[
                "action_id", "decision", "safety_level"
            ]].drop_duplicates("action_id"),
            on="action_id",
            how="left",
        )
    rollback_ids = {
        str(item.get("action_id"))
        for item in _read_list(safety_directory / "rollback_events.json")
    }
    aggregated["proposal_id"] = None
    aggregated["fallback"] = aggregated.get(
        "decision", pd.Series("", index=aggregated.index)
    ).isin(["fallback", "emergency_fallback"])
    aggregated["rollback"] = aggregated["action_id"].astype(str).isin(
        rollback_ids
    )
    return normalize_actions(aggregated)


def _optional_llm_target(
    mode: str, enable_real_llm: bool
) -> tuple[float | None, dict[str, Any]]:
    if mode != "llm_assisted":
        return None, {
            "llm_requests": 0,
            "llm_responses": 0,
            "llm_timeouts": 0,
            "valid_structured_outputs": 0,
            "invalid_structured_outputs": 0,
            "llm_limitations": [],
        }
    if not enable_real_llm:
        raise ValueError(
            "llm_assisted mode requires explicit enable_real_llm=True."
        )
    from energyplus.runtime_control.llm_adapter import (
        probe_live_runtime_context,
        request_runtime_llm_decision,
    )

    context = probe_live_runtime_context()
    outcome = asyncio.run(request_runtime_llm_decision(context))
    decision = outcome.decision
    target = (
        float(decision.proposed_setpoint_c)
        if decision is not None
        else None
    )
    return target, {
        "llm_requests": 1 if outcome.llm_called else 0,
        "llm_responses": 1 if outcome.llm_completed else 0,
        "llm_timeouts": int(outcome.error_code == "LLM_TIMEOUT"),
        "valid_structured_outputs": int(decision is not None),
        "invalid_structured_outputs": int(
            outcome.llm_completed and decision is None
        ),
        "llm_model": "qwen3:4b",
        "llm_prompt_version": "phase10-coarse-advisory-v1",
        "llm_limitations": [
            "One nondeterministic coarse advisory is bounded by the deterministic "
            "policy and every action still passes Phase 9."
        ],
    }


def run_controlled_evaluation(
    *,
    mode: Literal["reproducible_policy", "llm_assisted"] = "reproducible_policy",
    enable_real_llm: bool = False,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> ControlledEvaluationResult:
    """Run a complete annual EnergyPlus evaluation through Phases 8 and 9."""

    baseline = load_baseline_artifact(settings=settings)
    advisory_target, llm_metadata = _optional_llm_target(
        mode, enable_real_llm
    )
    provider = ReproduciblePolicyProvider(
        settings, advisory_target_c=advisory_target
    )
    runtime = run_phase8_runtime(
        provider,
        mode=f"phase10-{mode}",
        classification=CONTROLLED_CLASSIFICATION,
        real_llm_used=mode == "llm_assisted",
        generate_csv=True,
        require_provider_completion=False,
    )
    runtime_directory = runtime.artifact_directory
    output_directory = Path(runtime.summary["EnergyPlus_output_directory"])
    csv_path = Path(runtime.summary["EnergyPlus_csv_path"])
    if not csv_path.is_file():
        raise RuntimeError(
            f"Controlled EnergyPlus run did not produce CSV telemetry: {csv_path}"
        )
    inspection = inspect_baseline_model(
        ENERGYPLUS_BASELINE.resolve(ENERGYPLUS_BASELINE.base_model_path)
    )
    raw = normalize_energyplus_baseline_csv(
        csv_path, ENERGYPLUS_BASELINE, inspection
    )
    facility = normalize_facility(
        raw.facility,
        run_id=runtime_directory.name,
        classification=CONTROLLED_CLASSIFICATION,
    )
    zone = normalize_zone(raw.zone, run_id=runtime_directory.name)
    safety_directory = Path(
        runtime.summary["phase9_safety_artifact_directory"]
    )
    actions = _controlled_action_summary(
        runtime_directory, safety_directory
    )
    safety_summary = json.loads(
        (safety_directory / "summary.json").read_text(encoding="utf-8")
    )
    errors = parse_energyplus_error_file(output_directory / "eplusout.err")
    base_manifest = baseline.manifest
    model_path = ENERGYPLUS_BASELINE.resolve(
        ENERGYPLUS_BASELINE.baseline_model_path
    )
    weather_path = ENERGYPLUS_BASELINE.resolve(
        ENERGYPLUS_BASELINE.weather_file_path
    )
    manifest = {
        "manifest_version": 1,
        "generator_version": "ecopilot-phase10-controlled-v1",
        "run_id": runtime_directory.name,
        "mode": mode,
        "backend": "energyplus",
        "source": "EnergyPlus",
        "classification": CONTROLLED_CLASSIFICATION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_model_path": base_manifest["base_model_path"],
        "base_model_hash": base_manifest["base_model_hash"],
        "runtime_model_path": str(model_path),
        "runtime_model_hash": calculate_sha256(model_path),
        "derived_model_hash": calculate_sha256(model_path),
        "weather_path": str(weather_path),
        "weather_hash": calculate_sha256(weather_path),
        "energyplus_version": runtime.summary["EnergyPlus_version"],
        "run_period": base_manifest["run_period"],
        "reporting_frequency": base_manifest["reporting_frequency"],
        "interval_count": len(facility),
        "zone_display_mapping": base_manifest["zone_display_mapping"],
        "zone_mapping_hash": stable_json_hash(
            base_manifest["zone_display_mapping"]
        ),
        "occupancy_schedule_inventory": base_manifest[
            "occupancy_schedule_inventory"
        ],
        "occupancy_configuration_hash": stable_json_hash(
            base_manifest["occupancy_schedule_inventory"]
        ),
        "internal_load_schedule_inventory": base_manifest[
            "internal_load_schedule_inventory"
        ],
        "internal_load_configuration_hash": stable_json_hash(
            base_manifest["internal_load_schedule_inventory"]
        ),
        "control_policy": (
            "phase10-reproducible-policy-v1"
            if mode == "reproducible_policy"
            else "phase10-llm-bounded-policy-v1"
        ),
        "control_policy_configuration": {
            "controlled_zone": "SPACE1-1",
            "demand_trigger_kw": settings.demand_warning_kw,
            "demand_critical_kw": settings.demand_critical_kw,
            "setpoint_step_c": settings.controlled_setpoint_step_c,
            "occupied_comfort_bounds_c": [
                settings.occupied_temperature_min_c,
                settings.occupied_temperature_max_c,
            ],
            "phase9_final_authority": True,
            "phase8_actuator_path": True,
        },
        "actual_available_outputs": raw.actual_available_outputs,
        "runtime_artifact_directory": str(runtime_directory),
        "safety_artifact_directory": str(safety_directory),
        "files": {
            "facility_telemetry": "controlled_facility_telemetry.csv",
            "zone_telemetry": "controlled_zone_telemetry.csv",
            "actions": "controlled_action_summary.csv",
            "safety_summary": "controlled_safety_summary.json",
            "safety_decisions": "controlled_safety_decisions.json",
            "safety_rules": "controlled_safety_rules.json",
            "rollbacks": "controlled_rollback_events.json",
            "emergencies": "controlled_emergency_events.json",
            "proposals": "proposals.json",
        },
    }
    facility_total = float(facility["facility_electricity_kwh"].sum())
    summary = {
        "run_id": runtime_directory.name,
        "mode": mode,
        "backend": "energyplus",
        "source": "EnergyPlus",
        "classification": CONTROLLED_CLASSIFICATION,
        "official_result": True,
        "baseline_result": False,
        "development_result": False,
        "ai_controlled": mode == "llm_assisted",
        "closed_loop": True,
        "safety_supervised": True,
        "success": bool(
            runtime.success
            and len(facility) == baseline.identity.interval_count
            and errors.severe_count == 0
            and errors.fatal_count == 0
            and runtime.summary["control_injection_verified"]
        ),
        "energyplus_version": runtime.summary["EnergyPlus_version"],
        "model_path": str(model_path),
        "base_model_hash": base_manifest["base_model_hash"],
        "derived_model_hash": calculate_sha256(model_path),
        "weather_path": str(weather_path),
        "weather_hash": calculate_sha256(weather_path),
        "reporting_frequency": base_manifest["reporting_frequency"],
        "reporting_interval_count": len(facility),
        "zone_row_count": len(zone),
        "total_facility_electricity_kwh": facility_total,
        "control_injection_verified": bool(
            runtime.summary["control_injection_verified"]
        ),
        "actuator_reset_verified": bool(
            runtime.summary["actuator_reset_verified"]
        ),
        "safety_supervisor_enabled": True,
        "deterministic_safety_authority": True,
        "policy_opportunities": provider.policy_opportunities,
        "policy_resets": provider.policy_resets,
        "actuator_write_count": runtime.summary["actuator_write_count"],
        "safety_decision_count": runtime.summary["safety_decision_count"],
        "fallback_count": runtime.summary["fallback_count"],
        "rollback_count": runtime.summary["rollback_count"],
        "emergency_fallback_count": runtime.summary[
            "emergency_fallback_count"
        ],
        "warning_count": errors.warning_count,
        "severe_count": errors.severe_count,
        "fatal_count": errors.fatal_count,
        "runtime_artifact_directory": str(runtime_directory),
        "energyplus_output_directory": str(output_directory),
        "phase9_safety_artifact_directory": str(safety_directory),
        "actual_available_outputs": raw.actual_available_outputs,
        "complete_horizon": len(facility) == baseline.identity.interval_count,
        "final_optimization_result": False,
        "savings_result": False,
        **llm_metadata,
    }
    write_csv(
        runtime_directory / "controlled_facility_telemetry.csv", facility
    )
    write_csv(runtime_directory / "controlled_zone_telemetry.csv", zone)
    write_csv(runtime_directory / "controlled_action_summary.csv", actions)
    write_json(
        runtime_directory / "controlled_safety_summary.json", safety_summary
    )
    for source, target in (
        ("safety_decisions.json", "controlled_safety_decisions.json"),
        ("safety_rule_results.json", "controlled_safety_rules.json"),
        ("rollback_events.json", "controlled_rollback_events.json"),
        ("emergency_events.json", "controlled_emergency_events.json"),
    ):
        write_json(
            runtime_directory / target,
            _read_list(safety_directory / source),
        )
    write_json(runtime_directory / "controlled_manifest.json", manifest)
    write_json(runtime_directory / "controlled_summary.json", summary)
    return ControlledEvaluationResult(
        success=bool(summary["success"]),
        artifact_directory=runtime_directory,
        summary=summary,
    )


def _empty_metric_frame(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _comparison_inputs(
    baseline: LoadedRun, controlled: LoadedRun
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline_facility = normalize_facility(
        baseline.facility,
        run_id=baseline.identity.run_id,
        classification=baseline.identity.classification,
    )
    controlled_facility = normalize_facility(
        controlled.facility,
        run_id=controlled.identity.run_id,
        classification=controlled.identity.classification,
    )
    baseline_zone = normalize_zone(
        baseline.zone, run_id=baseline.identity.run_id
    )
    controlled_zone = normalize_zone(
        controlled.zone, run_id=controlled.identity.run_id
    )
    actions = normalize_actions(controlled.actions)
    return (
        baseline_facility,
        controlled_facility,
        baseline_zone,
        controlled_zone,
        actions,
    )


def run_comparison(
    *,
    baseline_path: Path | None = None,
    controlled_path: Path | None = None,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> ComparisonRunResult:
    baseline = load_baseline_artifact(baseline_path, settings=settings)
    controlled = load_controlled_artifact(controlled_path, settings=settings)
    (
        baseline_facility,
        controlled_facility,
        baseline_zone,
        controlled_zone,
        actions,
    ) = _comparison_inputs(baseline, controlled)
    compatibility = compare_run_compatibility(
        baseline.identity, controlled.identity, settings=settings
    )
    alignment = align_telemetry(
        baseline_facility,
        controlled_facility,
        baseline_zone,
        controlled_zone,
        expected_intervals=baseline.identity.interval_count,
    )
    official_calculation_allowed = bool(
        compatibility.comparable
        and (
            alignment.report["complete"]
            or not settings.require_complete_horizon
        )
    )
    if official_calculation_allowed:
        occupied_timestamps = (
            baseline_zone.loc[
                pd.to_numeric(
                    baseline_zone["occupancy"], errors="coerce"
                ).fillna(0)
                > 0,
                "timestamp",
            ]
            .drop_duplicates()
        )
        occupied_hours = float(len(occupied_timestamps))
        (
            baseline_energy,
            controlled_energy,
            energy_metrics,
            energy_frame,
        ) = calculate_energy_metrics(
            alignment.facility, occupied_hours=occupied_hours
        )
        demand_summary, demand_frame = calculate_demand_metrics(
            alignment.facility, settings=settings
        )
        (
            baseline_comfort,
            controlled_comfort,
            comfort_summary,
            comfort_frame,
        ) = calculate_comfort_metrics(alignment.zone, settings=settings)
        cost_summary, cost_frame = calculate_cost_metrics(
            energy_frame, settings=settings
        )
        carbon_summary, carbon_frame = calculate_carbon_metrics(
            energy_frame, settings=settings
        )
        facility_metric = energy_metrics[0]
        energy_reduction = facility_metric.absolute_reduction
        energy_percent = facility_metric.reduction_percent
    else:
        baseline_energy = controlled_energy = None
        demand_summary = {}
        comfort_summary = {"comfort_gate_passed": False}
        baseline_comfort = controlled_comfort = None
        cost_summary = carbon_summary = {}
        energy_frame = _empty_metric_frame([
            "timestamp",
            "baseline_energy_kwh",
            "controlled_energy_kwh",
            "interval_energy_reduction_kwh",
            "baseline_cumulative_energy_kwh",
            "controlled_cumulative_energy_kwh",
            "cumulative_energy_reduction_kwh",
        ])
        demand_frame = _empty_metric_frame([
            "timestamp", "baseline_demand_kw", "controlled_demand_kw"
        ])
        comfort_frame = _empty_metric_frame([
            "timestamp", "energyplus_zone_name"
        ])
        cost_frame = _empty_metric_frame([
            "timestamp", "baseline_cost", "controlled_cost"
        ])
        carbon_frame = _empty_metric_frame([
            "timestamp", "baseline_carbon_kg", "controlled_carbon_kg"
        ])
        energy_reduction = energy_percent = None
    safety_decisions = _read_list(
        controlled.directory / "controlled_safety_decisions.json"
    )
    safety_rules = _read_list(
        controlled.directory / "controlled_safety_rules.json"
    )
    rollbacks = _read_list(
        controlled.directory / "controlled_rollback_events.json"
    )
    emergencies = _read_list(
        controlled.directory / "controlled_emergency_events.json"
    )
    proposals = _read_list(controlled.directory / "proposals.json")
    reliability = calculate_reliability_metrics(
        expected_intervals=baseline.identity.interval_count,
        completed_intervals=int(alignment.report["matched_intervals"]),
        controlled_summary=controlled.summary,
        actions=actions,
        safety_decisions=safety_decisions,
        safety_summary=controlled.safety_summary,
    )
    agent = calculate_agent_metrics(
        proposals,
        control_mode=str(controlled.summary["mode"]),
        llm_requests=int(controlled.summary.get("llm_requests", 0)),
        valid_structured_outputs=int(
            controlled.summary.get("valid_structured_outputs", 0)
        ),
        invalid_structured_outputs=int(
            controlled.summary.get("invalid_structured_outputs", 0)
        ),
    )
    safety = calculate_safety_metrics(
        decisions=safety_decisions,
        rules=safety_rules,
        rollbacks=rollbacks,
        emergencies=emergencies,
    )
    comfort_gate = bool(comfort_summary.get("comfort_gate_passed"))
    claim = evaluate_claim_gate(
        compatibility_passed=compatibility.comparable,
        controlled_run_complete=bool(
            controlled.summary.get("complete_horizon")
        ),
        telemetry_alignment_passed=bool(alignment.report["complete"]),
        energy_reduction_kwh=energy_reduction,
        energy_reduction_percent=energy_percent,
        comfort_gate_passed=comfort_gate,
        emergency_comfort_breach=any(
            "COMFORT" in str(item.get("reason_code", ""))
            for item in emergencies
        ),
        severe_count=controlled.identity.severe_count,
        fatal_count=controlled.identity.fatal_count,
        control_injection_verified=(
            controlled.identity.control_injection_verified
        ),
        safety_supervisor_enabled=(
            controlled.identity.safety_supervisor_enabled
        ),
    )
    comparison_id = new_comparison_id()
    assumptions = [
        settings.tariff_source,
        settings.carbon_intensity_source,
        "Occupied comfort uses genuine PMV only when present; otherwise the "
        "declared occupied-temperature proxy is used.",
        "The deterministic policy changes only the verified SPACE1-1 cooling "
        "setpoint through the Phase 8 actuator and Phase 9 final authority.",
    ]
    limitations = [
        "The retained EnergyPlus People objects do not expose genuine PMV/PPD."
        if not baseline.summary.get("pmv_available")
        else "",
        "Tariff and carbon values are project assumptions, not EnergyPlus outputs.",
        *controlled.summary.get("llm_limitations", []),
    ]
    limitations = [item for item in limitations if item]
    summary_model = ComparisonSummary(
        comparison_id=comparison_id,
        comparison_valid=official_calculation_allowed,
        claim_status=claim.claim_status,
        eligible_to_claim_savings=claim.eligible_to_claim_savings,
        baseline_energy_kwh=(
            baseline_energy.total_energy_kwh if baseline_energy else None
        ),
        controlled_energy_kwh=(
            controlled_energy.total_energy_kwh if controlled_energy else None
        ),
        energy_reduction_kwh=energy_reduction,
        energy_reduction_percent=energy_percent,
        baseline_peak_demand_kw=(
            float(demand_summary["baseline_peak_demand_kw"])
            if demand_summary.get("baseline_peak_demand_kw") is not None
            else None
        ),
        controlled_peak_demand_kw=(
            float(demand_summary["controlled_peak_demand_kw"])
            if demand_summary.get("controlled_peak_demand_kw") is not None
            else None
        ),
        peak_reduction_percent=(
            float(demand_summary["peak_reduction_percent"])
            if demand_summary.get("peak_reduction_percent") is not None
            else None
        ),
        baseline_comfort_percent=(
            baseline_comfort.temperature_compliance_percent
            if baseline_comfort
            else None
        ),
        controlled_comfort_percent=(
            controlled_comfort.temperature_compliance_percent
            if controlled_comfort
            else None
        ),
        comfort_gate_passed=comfort_gate,
        cost_reduction=(
            float(cost_summary["absolute_cost_reduction"])
            if cost_summary.get("absolute_cost_reduction") is not None
            else None
        ),
        carbon_reduction=(
            float(carbon_summary["absolute_carbon_reduction_kg"])
            if carbon_summary.get("absolute_carbon_reduction_kg") is not None
            else None
        ),
        severe_count=controlled.identity.severe_count,
        fatal_count=controlled.identity.fatal_count,
        official_energyplus_comparison=official_calculation_allowed,
        safety_supervisor_enabled=(
            controlled.identity.safety_supervisor_enabled
        ),
        control_injection_verified=(
            controlled.identity.control_injection_verified
        ),
        telemetry_alignment_passed=bool(alignment.report["complete"]),
        reproducible=False,
        exact_approved_statement=claim.approved_statement,
        assumptions=assumptions,
        limitations=limitations,
    )
    final_summary = summary_model.model_dump(mode="json")
    final_summary.update({
        "comparison_mode": controlled.summary["mode"],
        "baseline_run_id": baseline.identity.run_id,
        "controlled_run_id": controlled.identity.run_id,
        "compatibility_status": compatibility.status,
        "alignment": alignment.report,
        "energy_components": {
            "baseline": (
                baseline_energy.model_dump(mode="json")
                if baseline_energy else None
            ),
            "controlled": (
                controlled_energy.model_dump(mode="json")
                if controlled_energy else None
            ),
        },
        "demand_metrics": demand_summary,
        "comfort_metrics": comfort_summary,
        "cost_metrics": cost_summary,
        "carbon_metrics": carbon_summary,
        "claim_gate": claim.model_dump(mode="json"),
    })
    reproducibility = ReproducibilityReport(
        reproducible=False,
        mode=str(controlled.summary["mode"]),
        first_comparison_id=comparison_id,
        second_comparison_id=None,
        model_hashes_match=True,
        weather_hashes_match=True,
        telemetry_shape_match=True,
        energy_within_tolerance=False,
        peak_demand_within_tolerance=False,
        comfort_within_tolerance=False,
        action_counts_match=False,
        comparison_status_match=False,
        mismatches=["Independent deterministic repeat not yet executed."],
        limitations=(
            ["LLM-assisted outputs are not expected to be bit-identical."]
            if controlled.summary["mode"] == "llm_assisted"
            else []
        ),
        tolerance=settings.reproducibility_tolerance,
    )
    executive = build_executive_summary(
        final_summary,
        compatibility_status=compatibility.status,
        baseline_run_id=baseline.identity.run_id,
        controlled_run_id=controlled.identity.run_id,
        control_mode=str(controlled.summary["mode"]),
    )
    judge = {
        key: final_summary[key]
        for key in (
            "comparison_id",
            "comparison_valid",
            "claim_status",
            "eligible_to_claim_savings",
            "baseline_energy_kwh",
            "controlled_energy_kwh",
            "energy_reduction_kwh",
            "energy_reduction_percent",
            "baseline_peak_demand_kw",
            "controlled_peak_demand_kw",
            "peak_reduction_percent",
            "baseline_comfort_percent",
            "controlled_comfort_percent",
            "comfort_gate_passed",
            "severe_count",
            "fatal_count",
            "official_energyplus_comparison",
            "safety_supervisor_enabled",
            "control_injection_verified",
            "telemetry_alignment_passed",
            "exact_approved_statement",
        )
    }
    directory = write_comparison_bundle(
        comparison_id=comparison_id,
        baseline_summary=baseline.summary,
        controlled_summary=controlled.summary,
        compatibility_report=compatibility.model_dump(mode="json"),
        final_summary=final_summary,
        judge_summary=judge,
        reliability_metrics=reliability.model_dump(mode="json"),
        agent_metrics=agent.model_dump(mode="json"),
        safety_metrics=safety.model_dump(mode="json"),
        reproducibility_report=reproducibility.model_dump(mode="json"),
        executive_summary=executive,
        energy_comparison=energy_frame,
        demand_comparison=demand_frame,
        comfort_comparison=comfort_frame,
        cost_comparison=cost_frame,
        carbon_comparison=carbon_frame,
        action_summary=actions,
        aligned_facility=alignment.facility,
        aligned_zone=alignment.zone,
        baseline_artifact=baseline.directory,
        controlled_artifact=controlled.directory,
        settings=settings,
    )
    return ComparisonRunResult(
        success=official_calculation_allowed,
        artifact_directory=directory,
        summary=final_summary,
    )


__all__ = [
    "CONTROLLED_CLASSIFICATION",
    "ComparisonRunResult",
    "ControlledEvaluationResult",
    "ReproduciblePolicyProvider",
    "run_comparison",
    "run_controlled_evaluation",
]
