"""Orchestrate the official fixed-schedule EnergyPlus baseline without fallback."""

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
import uuid
from typing import Any

import pandas as pd

from config.settings import ENERGYPLUS
from energyplus.adapter.discovery import discover_energyplus
from energyplus.adapter.error_parser import (
    classify_energyplus_warning,
    parse_energyplus_error_file,
)
from energyplus.adapter.runner import EnergyPlusRunResult, run_energyplus
from energyplus.baseline.artifacts import json_safe, write_baseline_artifacts
from energyplus.baseline.manifest import (
    calculate_sha256,
    create_baseline_manifest,
)
from energyplus.baseline.metrics import BaselineMetrics, calculate_baseline_metrics
from energyplus.baseline.model_builder import (
    BASELINE_OUTPUT_METERS,
    BASELINE_OUTPUT_VARIABLES,
    BaselineModelBuildResult,
    build_phase5_baseline_model,
)
from energyplus.baseline.normalizer import (
    NormalizedBaselineTelemetry,
    normalize_energyplus_baseline_csv,
)
from energyplus.baseline.schedule_inspector import inspect_baseline_model
from energyplus.baseline.settings import (
    ENERGYPLUS_BASELINE,
    EnergyPlusBaselineSettings,
)


@dataclass
class EnergyPlusBaselineRunResult:
    run_id: str
    success: bool
    backend_id: str = "energyplus"
    source: str = "EnergyPlus"
    classification: str = "official_energyplus_baseline"
    official_result: bool = False
    baseline_result: bool = False
    ai_controlled: bool = False
    closed_loop: bool = False
    optimized: bool = False
    savings_result: bool = False
    model_build_result: BaselineModelBuildResult | None = None
    energyplus_run_result: EnergyPlusRunResult | None = None
    zone_telemetry: pd.DataFrame = field(default_factory=pd.DataFrame)
    facility_telemetry: pd.DataFrame = field(default_factory=pd.DataFrame)
    zone_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    schedule_boundary_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    baseline_summary: dict[str, Any] = field(default_factory=dict)
    artifact_paths: dict[str, Path] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)
    manifest_path: Path | None = None
    reproducibility_status: Any | None = None
    warnings: tuple[str, ...] = ()
    failure_reason: str | None = None


def _run_id() -> str:
    return (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )


def _failed(
    identifier: str,
    reason: str,
    *,
    build: BaselineModelBuildResult | None = None,
    run: EnergyPlusRunResult | None = None,
    warnings: tuple[str, ...] = (),
) -> EnergyPlusBaselineRunResult:
    return EnergyPlusBaselineRunResult(
        run_id=identifier,
        success=False,
        model_build_result=build,
        energyplus_run_result=run,
        warnings=warnings,
        failure_reason=reason,
    )


def _requested_output_names() -> list[str]:
    return [
        *(name for _, name in BASELINE_OUTPUT_VARIABLES),
        *BASELINE_OUTPUT_METERS,
        "Output:SQLite",
        "Output:VariableDictionary",
    ]


def _warning_records(run: EnergyPlusRunResult) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    parsed = (
        parse_energyplus_error_file(run.error_file_path)
        if run.error_file_path else None
    )
    records = []
    messages = []
    for record in parsed.records if parsed else ():
        item = json_safe(asdict(record))
        if record.severity == "warning":
            item["classification"] = classify_energyplus_warning(record.message)
            messages.append(record.message)
        records.append(item)
    return records, tuple(messages)


def _baseline_summary(
    *,
    identifier: str,
    settings: EnergyPlusBaselineSettings,
    build: BaselineModelBuildResult,
    run: EnergyPlusRunResult,
    metrics: BaselineMetrics,
    telemetry: NormalizedBaselineTelemetry,
    version: str | None,
    weather_hash: str,
) -> dict[str, Any]:
    zone_roles = telemetry.zone[
        ["energyplus_zone_name", "zone_role"]
    ].drop_duplicates()
    occupied_zone_count = int(
        zone_roles["zone_role"].map(
            lambda value: "occupied" in str(value).casefold()
            and str(value).casefold() != "plenum"
        ).sum()
    )
    plenum_zone_count = int(
        (zone_roles["zone_role"].str.casefold() == "plenum").sum()
    )
    return {
        "run_id": identifier,
        "backend": "energyplus",
        "source": "EnergyPlus",
        "classification": "official_energyplus_baseline",
        "official_result": True,
        "baseline_result": True,
        "ai_controlled": False,
        "closed_loop": False,
        "optimized": False,
        "savings_result": False,
        "energyplus_version": version,
        "model_path": str(build.destination_model_path),
        "model_hash": build.destination_model_hash,
        "base_model_path": str(build.source_model_path),
        "base_model_hash": build.source_model_hash,
        "derived_model_hash": build.destination_model_hash,
        "weather_path": str(settings.resolve(settings.weather_file_path)),
        "weather_hash": weather_hash,
        "reporting_frequency": settings.reporting_frequency,
        "timestamp_convention": telemetry.timestamp_convention,
        "zone_count": int(telemetry.zone["energyplus_zone_name"].nunique()),
        "occupied_zone_count": occupied_zone_count,
        "plenum_zone_count": plenum_zone_count,
        **metrics.summary,
        "warning_count": run.warning_count,
        "severe_count": run.severe_count,
        "fatal_count": run.fatal_count,
        "success": True,
        "actual_available_outputs": telemetry.actual_available_outputs,
    }


def run_energyplus_baseline(
    settings: EnergyPlusBaselineSettings | None = None,
    run_id: str | None = None,
    rebuild_model: bool = True,
) -> EnergyPlusBaselineRunResult:
    """Build, execute, normalize, measure, and persist the official baseline."""
    resolved = settings or ENERGYPLUS_BASELINE
    identifier = run_id or _run_id()
    source = resolved.resolve(resolved.base_model_path)
    destination = resolved.resolve(resolved.baseline_model_path)
    weather = resolved.resolve(resolved.weather_file_path)
    output_root = resolved.resolve(resolved.official_output_root)
    metadata_root = resolved.resolve(resolved.metadata_root)
    discovery_settings = replace(
        ENERGYPLUS,
        base_model_path=source,
        weather_file_path=weather,
        output_root=output_root,
        metadata_root=metadata_root,
    )
    status = discover_energyplus(discovery_settings)
    if not status.ready_for_run:
        return _failed(
            identifier,
            "EnergyPlus baseline environment is not ready: "
            + "; ".join(status.readiness_issues),
        )
    if not weather.is_file():
        return _failed(identifier, f"Weather file is missing: {weather}")

    if rebuild_model:
        build = build_phase5_baseline_model(source, destination, resolved)
    else:
        if not destination.is_file():
            return _failed(identifier, f"Baseline model is missing: {destination}")
        inspection = inspect_baseline_model(source)
        build = BaselineModelBuildResult(
            success=True,
            source_model_path=source,
            destination_model_path=destination,
            source_model_hash=calculate_sha256(source),
            destination_model_hash=calculate_sha256(destination),
            schedules_inspected=len(inspection.schedules),
            schedules_modified=(),
            output_requests_added=(),
            warnings=(),
            assumptions=("Existing deterministic Phase 5 model reused.",),
            failure_reason=None,
            inspection_metadata_path=destination.with_suffix(".inspection.json"),
            inspection=inspection,
        )
    if not build.success:
        return _failed(
            identifier,
            "Phase 5 baseline model build failed: "
            + (build.failure_reason or "unknown model-build error"),
            build=build,
        )
    run_settings = replace(
        discovery_settings,
        base_model_path=destination,
        output_root=output_root,
        metadata_root=metadata_root,
    )
    try:
        energyplus_result = run_energyplus(run_settings, run_id=identifier)
    except (FileExistsError, OSError, RuntimeError) as error:
        return _failed(
            identifier,
            f"EnergyPlus baseline execution failed: {error}",
            build=build,
        )
    warning_records, warning_messages = _warning_records(energyplus_result)
    if not energyplus_result.success:
        return _failed(
            identifier,
            energyplus_result.failure_reason or "EnergyPlus baseline run failed.",
            build=build,
            run=energyplus_result,
            warnings=warning_messages,
        )
    if energyplus_result.severe_count or energyplus_result.fatal_count:
        return _failed(
            identifier,
            "EnergyPlus baseline contains severe or fatal diagnostics.",
            build=build,
            run=energyplus_result,
            warnings=warning_messages,
        )
    if energyplus_result.csv_output_path is None:
        return _failed(
            identifier,
            "EnergyPlus baseline did not produce CSV telemetry.",
            build=build,
            run=energyplus_result,
            warnings=warning_messages,
        )
    try:
        normalized = normalize_energyplus_baseline_csv(
            energyplus_result.csv_output_path,
            resolved,
            build.inspection,
        )
        required = {
            "zone temperature": normalized.actual_available_outputs[
                "zone_temperature"
            ],
            "facility electricity": normalized.actual_available_outputs[
                "facility_electricity"
            ],
            "facility demand": normalized.actual_available_outputs[
                "facility_demand"
            ],
            "outdoor temperature": normalized.actual_available_outputs[
                "outdoor_temperature"
            ],
            "thermostat cooling setpoint": normalized.actual_available_outputs[
                "cooling_setpoint"
            ],
        }
        missing = [name for name, available in required.items() if not available]
        if missing:
            raise ValueError(
                "Missing required Phase 5 telemetry: " + ", ".join(missing)
            )
        metrics = calculate_baseline_metrics(normalized, resolved)
        adherence = metrics.summary.get("thermostat_adherence_percent")
        if adherence is None or adherence < 100.0 - 1e-9:
            raise ValueError(
                "Configured thermostat schedule was not applied to every "
                f"available conditioned-zone record (adherence={adherence})."
            )
    except (FileNotFoundError, KeyError, TypeError, ValueError) as error:
        return _failed(
            identifier,
            f"Phase 5 telemetry validation failed: {error}",
            build=build,
            run=energyplus_result,
            warnings=warning_messages,
        )

    weather_hash = calculate_sha256(weather)
    summary = _baseline_summary(
        identifier=identifier,
        settings=resolved,
        build=build,
        run=energyplus_result,
        metrics=metrics,
        telemetry=normalized,
        version=status.detected_version,
        weather_hash=weather_hash,
    )
    inspection = build.inspection or inspect_baseline_model(source)
    thermostat_policy = {
        "occupied_start_hour": resolved.occupied_start_hour,
        "occupied_end_hour": resolved.occupied_end_hour,
        "cooling": {
            "unoccupied_c": resolved.unoccupied_cooling_setpoint_c,
            "occupied_c": resolved.occupied_cooling_setpoint_c,
        },
        "heating": {
            "unoccupied_c": resolved.unoccupied_heating_setpoint_c,
            "occupied_c": resolved.occupied_heating_setpoint_c,
        },
        "comfort_range_c": [
            resolved.occupied_temperature_min_c,
            resolved.occupied_temperature_max_c,
        ],
        "pmv_range": [resolved.pmv_min, resolved.pmv_max],
        "hourly_timestamp_interpretation": "interval end",
    }
    manifest = create_baseline_manifest(
        run_id=identifier,
        energyplus_version=status.detected_version,
        executable_path=status.executable_path,
        base_model_path=source,
        base_model_hash=build.source_model_hash or calculate_sha256(source),
        derived_model_path=destination,
        derived_model_hash=(
            build.destination_model_hash or calculate_sha256(destination)
        ),
        weather_path=weather,
        weather_hash=weather_hash,
        reporting_frequency=resolved.reporting_frequency,
        inspection=inspection,
        thermostat_policy=thermostat_policy,
        zone_mapping=dict(resolved.zone_display_names),
        zone_roles=dict(resolved.zone_roles),
        requested_outputs=_requested_output_names(),
        actual_available_outputs=normalized.actual_available_outputs,
        warnings=warning_records,
    )
    errors = {
        "run_id": identifier,
        "warning_count": energyplus_result.warning_count,
        "severe_count": energyplus_result.severe_count,
        "fatal_count": energyplus_result.fatal_count,
        "records": warning_records,
    }
    metadata = {
        "run_id": identifier,
        "energyplus_run_result": json_safe(asdict(energyplus_result)),
        "model_build_result": {
            key: json_safe(value)
            for key, value in asdict(build).items()
            if key != "inspection"
        },
        "schedule_boundary_validation": json_safe(
            metrics.schedule_boundary_table.to_dict(orient="records")
        ),
        "source_columns": list(normalized.source_columns),
        "actual_available_outputs": normalized.actual_available_outputs,
    }
    artifact_paths = write_baseline_artifacts(
        success=True,
        results_root=resolved.resolve(resolved.official_results_root),
        zone_telemetry=normalized.zone,
        facility_telemetry=normalized.facility,
        zone_summary=metrics.zone_summary,
        summary=summary,
        errors=errors,
        metadata=metadata,
        manifest=manifest,
    )
    return EnergyPlusBaselineRunResult(
        run_id=identifier,
        success=True,
        official_result=True,
        baseline_result=True,
        model_build_result=build,
        energyplus_run_result=energyplus_result,
        zone_telemetry=normalized.zone,
        facility_telemetry=normalized.facility,
        zone_summary=metrics.zone_summary,
        schedule_boundary_table=metrics.schedule_boundary_table,
        baseline_summary=summary,
        artifact_paths=artifact_paths,
        manifest=manifest,
        manifest_path=artifact_paths.get("manifest"),
        warnings=warning_messages,
    )


__all__ = [
    "EnergyPlusBaselineRunResult",
    "run_energyplus_baseline",
]
