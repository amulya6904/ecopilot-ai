"""Deterministic scientific compatibility gate for Phase 10 runs."""

from typing import Any

from .schemas import (
    CompatibilityCheck,
    CompatibilityReport,
    RunIdentity,
)
from .settings import COMPARISON_SETTINGS, ComparisonSettings


def _check(
    check_id: str,
    passed: bool,
    baseline: Any,
    controlled: Any,
    message: str,
    *,
    required: bool = True,
) -> CompatibilityCheck:
    return CompatibilityCheck(
        check_id=check_id,
        passed=bool(passed),
        required=required,
        baseline_value=baseline,
        controlled_value=controlled,
        message=message,
    )


def compare_run_compatibility(
    baseline: RunIdentity,
    controlled: RunIdentity,
    *,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> CompatibilityReport:
    """Return every compatibility check; never hide a failed condition."""

    checks = [
        _check(
            "ENERGYPLUS_BACKEND",
            baseline.backend.casefold() == settings.required_backend
            and controlled.backend.casefold() == settings.required_backend,
            baseline.backend,
            controlled.backend,
            "Both runs must use the EnergyPlus backend.",
        ),
        _check(
            "ENERGYPLUS_SOURCE",
            baseline.source == settings.required_source
            and controlled.source == settings.required_source,
            baseline.source,
            controlled.source,
            "Both runs must identify EnergyPlus as their source.",
        ),
        _check(
            "ACCEPTED_CLASSIFICATION",
            baseline.classification == "official_energyplus_baseline"
            and controlled.classification
            == "official_energyplus_safety_supervised_controlled_evaluation",
            baseline.classification,
            controlled.classification,
            "Official baseline and controlled classifications are required.",
        ),
        _check(
            "RUN_COMPLETED",
            baseline.success and controlled.success,
            baseline.success,
            controlled.success,
            "Both simulations must complete successfully.",
        ),
        _check(
            "BASE_MODEL_HASH",
            bool(baseline.base_model_hash)
            and baseline.base_model_hash == controlled.base_model_hash,
            baseline.base_model_hash,
            controlled.base_model_hash,
            "The immutable base-model hash must match.",
        ),
        _check(
            "DERIVED_MODEL_RELATIONSHIP",
            bool(baseline.derived_model_hash)
            and baseline.derived_model_hash == controlled.derived_model_hash,
            baseline.derived_model_hash,
            controlled.derived_model_hash,
            "The controlled run must execute the same derived Phase 5 model.",
        ),
        _check(
            "WEATHER_HASH",
            bool(baseline.weather_hash)
            and baseline.weather_hash == controlled.weather_hash,
            baseline.weather_hash,
            controlled.weather_hash,
            "Weather files must be byte-identical.",
        ),
        _check(
            "ENERGYPLUS_VERSION",
            bool(baseline.energyplus_version)
            and baseline.energyplus_version == controlled.energyplus_version,
            baseline.energyplus_version,
            controlled.energyplus_version,
            "EnergyPlus versions must match.",
        ),
        _check(
            "RUN_PERIOD",
            bool(baseline.run_period)
            and baseline.run_period == controlled.run_period,
            baseline.run_period,
            controlled.run_period,
            "Simulation periods and initial calendar settings must match.",
        ),
        _check(
            "REPORTING_FREQUENCY",
            bool(baseline.reporting_frequency)
            and baseline.reporting_frequency.casefold()
            == controlled.reporting_frequency.casefold(),
            baseline.reporting_frequency,
            controlled.reporting_frequency,
            "Reporting frequencies must match.",
        ),
        _check(
            "OCCUPANCY_CONFIGURATION",
            bool(baseline.occupancy_configuration_hash)
            and baseline.occupancy_configuration_hash
            == controlled.occupancy_configuration_hash,
            baseline.occupancy_configuration_hash,
            controlled.occupancy_configuration_hash,
            "Occupancy configuration hashes must match.",
        ),
        _check(
            "INTERNAL_LOAD_CONFIGURATION",
            baseline.internal_load_configuration_hash is not None
            and baseline.internal_load_configuration_hash
            == controlled.internal_load_configuration_hash,
            baseline.internal_load_configuration_hash,
            controlled.internal_load_configuration_hash,
            "Internal-load configuration hashes must match when available.",
        ),
        _check(
            "ZONE_MAPPING",
            bool(baseline.zone_mapping_hash)
            and baseline.zone_mapping_hash == controlled.zone_mapping_hash,
            baseline.zone_mapping_hash,
            controlled.zone_mapping_hash,
            "Zone mappings must match.",
        ),
        _check(
            "EXPECTED_INTERVALS",
            baseline.interval_count > 0
            and baseline.interval_count == controlled.interval_count,
            baseline.interval_count,
            controlled.interval_count,
            "Complete runs must contain the same expected interval count.",
        ),
        _check(
            "CRITICAL_TELEMETRY",
            baseline.critical_telemetry_complete
            and controlled.critical_telemetry_complete,
            baseline.critical_telemetry_complete,
            controlled.critical_telemetry_complete,
            "Critical energy, demand, weather, occupancy, and zone telemetry is required.",
        ),
        _check(
            "ZERO_SEVERE_ERRORS",
            not settings.require_zero_severe_errors
            or (baseline.severe_count == 0 and controlled.severe_count == 0),
            baseline.severe_count,
            controlled.severe_count,
            "Both runs must satisfy the configured severe-error policy.",
        ),
        _check(
            "ZERO_FATAL_ERRORS",
            not settings.require_zero_fatal_errors
            or (baseline.fatal_count == 0 and controlled.fatal_count == 0),
            baseline.fatal_count,
            controlled.fatal_count,
            "Both runs must satisfy the configured fatal-error policy.",
        ),
        _check(
            "CONTROL_INJECTION_VERIFIED",
            controlled.control_injection_verified,
            False,
            controlled.control_injection_verified,
            "The controlled run must contain a verified actuator change.",
        ),
        _check(
            "SAFETY_SUPERVISOR_ENABLED",
            controlled.safety_supervisor_enabled,
            False,
            controlled.safety_supervisor_enabled,
            "The deterministic Phase 9 safety supervisor must have final authority.",
        ),
    ]
    failed_required = [
        item.check_id for item in checks if item.required and not item.passed
    ]
    failed_optional = [
        item.check_id for item in checks if not item.required and not item.passed
    ]
    if not failed_required:
        status = "comparable"
    elif settings.allow_conditionally_comparable:
        status = "conditionally_comparable"
    else:
        status = "not_comparable"
    return CompatibilityReport(
        status=status,
        comparable=status == "comparable",
        conditionally_comparable=status == "conditionally_comparable",
        checks=checks,
        failed_required_checks=failed_required,
        warnings=[
            *(f"Optional check failed: {name}" for name in failed_optional),
            *(
                [
                    "Conditional comparisons are enabled; official savings remain gated."
                ]
                if status == "conditionally_comparable"
                else []
            ),
        ],
    )


__all__ = ["compare_run_compatibility"]
