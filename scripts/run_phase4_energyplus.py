"""Run the first real EnergyPlus Phase 4 batch validation."""

from backends.energyplus import EnergyPlusBackend
from config.settings import ENERGYPLUS
from energyplus.adapter.output_requests import ensure_phase4_output_requests


def main() -> int:
    ensure_phase4_output_requests(
        ENERGYPLUS.source_model_path,
        ENERGYPLUS.base_model_path,
    )
    backend = EnergyPlusBackend()
    status = backend.availability_status()
    print(f"Backend: {backend.display_name}")
    print(f"Installation detected: {status.installed}")
    print(f"Detected version: {status.detected_version or 'Unavailable'}")
    print(f"Executable: {status.executable_path or 'Not found'}")
    print(f"IDF: {backend.settings.base_model_path}")
    print(f"EPW: {backend.settings.weather_file_path}")
    print(f"Model ready: {status.model_exists}")
    print(f"Weather ready: {status.weather_exists}")
    print(f"Simulation environment ready: {status.ready_for_run}")
    if not status.ready_for_run:
        for issue in status.readiness_issues:
            print(f"Readiness issue: {issue}")
        return 2
    result = backend.run_simulation()
    print(f"Run ID: {result.run_id}")
    print(f"Success: {result.success}")
    print(f"Exit code: {result.exit_code}")
    print(f"Duration: {result.duration_seconds:.2f} seconds")
    print(f"Warnings: {result.warning_count}")
    print(f"Severe errors: {result.severe_count}")
    print(f"Fatal errors: {result.fatal_count}")
    print(f"Output directory: {result.output_dir}")
    print(f"Classification: {result.classification}")
    print(f"Official EnergyPlus-derived result: {result.official_result}")
    summary = backend.get_telemetry_summary()
    if summary is not None:
        print(f"Telemetry rows: {summary.row_count}")
        print(f"Detected zones: {len(summary.zones)}")
        print(f"Zone temperature available: {summary.zone_temperature_available}")
        print(f"Outdoor temperature available: {summary.outdoor_temperature_available}")
        print(f"Electricity available: {summary.electricity_available}")
        print(f"Demand available: {summary.demand_available}")
        print(f"Total electricity (kWh): {summary.total_electricity_kwh}")
        print(f"Peak demand (kW): {summary.peak_demand_kw}")
        print(f"Electricity source column: {summary.electricity_source_column}")
        print(f"Demand source column: {summary.demand_source_column}")
        print(f"Demand method: {summary.demand_calculation_method}")
        required = (
            summary.zone_temperature_available
            and summary.outdoor_temperature_available
            and summary.electricity_available
            and summary.demand_available
        )
        if not required:
            print("Failure reason: Required Phase 4 telemetry is missing.")
            return 1
    if result.failure_reason:
        print(f"Failure reason: {result.failure_reason}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
