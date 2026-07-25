"""Run the official fixed-schedule EnergyPlus baseline and optional repeat check."""

import argparse
from dataclasses import asdict
from pathlib import Path

from config.settings import ENERGYPLUS
from energyplus.adapter.discovery import discover_energyplus
from energyplus.baseline.artifacts import write_reproducibility_report
from energyplus.baseline.model_builder import (
    COOLING_SCHEDULE_NAME,
    HEATING_SCHEDULE_NAME,
    build_phase5_baseline_model,
)
from energyplus.baseline.reproducibility import compare_baseline_runs
from energyplus.baseline.runner import run_energyplus_baseline
from energyplus.baseline.schedule_inspector import inspect_baseline_model
from energyplus.baseline.settings import ENERGYPLUS_BASELINE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EcoPilot AI Phase 5 official EnergyPlus baseline"
    )
    parser.add_argument(
        "--verify-reproducibility",
        action="store_true",
        help="run a second real baseline and compare frozen inputs and results",
    )
    return parser


def _print_result(result) -> None:
    run = result.energyplus_run_result
    summary = result.baseline_summary
    print(f"Run ID: {result.run_id}")
    print(f"Success: {result.success}")
    print(f"Exit code: {run.exit_code if run else 'Unavailable'}")
    print(
        "Duration: "
        + (f"{run.duration_seconds:.2f} seconds" if run else "Unavailable")
    )
    print(f"Warnings: {run.warning_count if run else 0}")
    print(f"Severe errors: {run.severe_count if run else 0}")
    print(f"Fatal errors: {run.fatal_count if run else 0}")
    print(f"Zone count: {summary.get('zone_count', 'Unavailable')}")
    print(
        "Occupied-zone count: "
        f"{summary.get('occupied_zone_count', 'Unavailable')}"
    )
    print(
        "Total facility electricity: "
        f"{summary.get('total_facility_electricity_kwh')} kWh"
    )
    print(
        "Average demand: "
        f"{summary.get('average_facility_demand_kw')} kW"
    )
    print(
        f"Peak demand: {summary.get('peak_facility_demand_kw')} kW"
    )
    print(f"Peak-demand timestamp: {summary.get('peak_demand_timestamp')}")
    print(
        "Thermostat adherence: "
        f"{summary.get('thermostat_adherence_percent')}%"
    )
    print(f"Occupancy available: {summary.get('occupancy_available')}")
    print(f"Occupancy source: {summary.get('occupancy_source')}")
    print(
        "Temperature compliance: "
        f"{summary.get('temperature_compliance_percent')}%"
    )
    print(f"PMV available: {summary.get('pmv_available')}")
    print(f"PMV compliance: {summary.get('pmv_compliance_percent')}")
    print(f"Classification: {result.classification}")
    print(f"Official result: {result.official_result}")
    print(f"Baseline result: {result.baseline_result}")
    print(f"AI controlled: {result.ai_controlled}")
    print(f"Closed loop: {result.closed_loop}")
    print(f"Optimized: {result.optimized}")
    print(f"Savings result: {result.savings_result}")
    if run:
        print(f"Raw EnergyPlus output: {run.output_dir}")
    print("Artifact paths:")
    for name, path in result.artifact_paths.items():
        print(f"  {name}: {path}")
    if result.failure_reason:
        print(f"Failure reason: {result.failure_reason}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    settings = ENERGYPLUS_BASELINE
    source = settings.resolve(settings.base_model_path)
    destination = settings.resolve(settings.baseline_model_path)
    weather = settings.resolve(settings.weather_file_path)
    discovery_settings = ENERGYPLUS.__class__(
        **{
            **vars(ENERGYPLUS),
            "base_model_path": source,
            "weather_file_path": weather,
            "output_root": settings.resolve(settings.official_output_root),
            "metadata_root": settings.resolve(settings.metadata_root),
        }
    )
    status = discover_energyplus(discovery_settings)
    print("Phase 5 — Official Fixed-Schedule EnergyPlus Baseline")
    print(f"EnergyPlus ready: {status.ready_for_run}")
    print(f"EnergyPlus version: {status.detected_version or 'Not detected'}")
    print(f"Executable: {status.executable_path or 'Not found'}")
    print(f"Source model: {source}")
    print(f"Baseline model destination: {destination}")
    print(f"Weather file: {weather}")
    print(f"Reporting frequency: {settings.reporting_frequency}")
    print("Zone display mapping:")
    for technical_name, display_name in settings.zone_display_names.items():
        print(
            f"  {technical_name} -> {display_name} "
            f"({settings.zone_roles[technical_name]})"
        )
    if not status.ready_for_run:
        for issue in status.readiness_issues:
            print(f"Readiness issue: {issue}")
        return 2
    inspection = inspect_baseline_model(source)
    print(f"IDF objects inspected: {inspection.object_count}")
    print(f"Schedules inspected: {len(inspection.schedules)}")
    print(
        "Existing cooling schedules: "
        + ", ".join(inspection.cooling_schedule_names)
    )
    print(
        "Existing heating schedules: "
        + ", ".join(inspection.heating_schedule_names)
    )
    build = build_phase5_baseline_model(source, destination, settings)
    print(f"Baseline model build success: {build.success}")
    print("Modified thermostat-setpoint objects: " + ", ".join(
        build.schedules_modified
    ))
    print(f"Baseline cooling schedule: {COOLING_SCHEDULE_NAME}")
    print(
        "  00:00–09:00 -> "
        f"{settings.unoccupied_cooling_setpoint_c:g}°C; "
        "09:00–18:00 -> "
        f"{settings.occupied_cooling_setpoint_c:g}°C; "
        "18:00–24:00 -> "
        f"{settings.unoccupied_cooling_setpoint_c:g}°C"
    )
    print(f"Baseline heating schedule: {HEATING_SCHEDULE_NAME}")
    print(
        "  00:00–09:00 -> "
        f"{settings.unoccupied_heating_setpoint_c:g}°C; "
        "09:00–18:00 -> "
        f"{settings.occupied_heating_setpoint_c:g}°C; "
        "18:00–24:00 -> "
        f"{settings.unoccupied_heating_setpoint_c:g}°C"
    )
    print("Output requests added: " + ", ".join(build.output_requests_added))
    if not build.success:
        print(f"Failure reason: {build.failure_reason}")
        return 1
    first = run_energyplus_baseline(settings, rebuild_model=False)
    _print_result(first)
    if not first.success:
        return 1
    if not args.verify_reproducibility:
        return 0
    print("\nRunning second real EnergyPlus baseline for reproducibility...")
    second = run_energyplus_baseline(settings, rebuild_model=True)
    _print_result(second)
    if not second.success:
        return 1
    report = compare_baseline_runs(
        first, second, settings.reproducibility_tolerance
    )
    report_path = write_reproducibility_report(
        settings.resolve(settings.official_results_root),
        asdict(report),
    )
    print(f"Reproducible: {report.reproducible}")
    print(f"Exact input match: {report.exact_input_match}")
    print(
        "Energy absolute difference: "
        f"{report.energy_absolute_difference_kwh} kWh"
    )
    print(
        f"Peak-demand difference: {report.peak_demand_difference_kw} kW"
    )
    print(f"Telemetry shape match: {report.telemetry_shape_match}")
    print(f"Warnings match: {report.warnings_match}")
    for mismatch in report.mismatches:
        print(f"Mismatch: {mismatch}")
    print(f"Reproducibility artifact: {report_path}")
    return 0 if report.reproducible else 1


if __name__ == "__main__":
    raise SystemExit(main())
