"""Run, summarize, and export the Phase 3 lightweight development baseline."""

from pathlib import Path

import pandas as pd

from config.settings import BASELINE, OPTIMIZATION
from controllers.baseline import BaselineController, run_baseline_day
from metrics.baseline_metrics import calculate_baseline_summary, calculate_zone_summary
from simulator.building import BuildingSimulator


def export_baseline_results(
    results: pd.DataFrame, zone_summary: pd.DataFrame, output_directory: Path
) -> tuple[Path, Path]:
    """Export full and zone-summary CSV files, replacing earlier generated files."""
    output_directory.mkdir(parents=True, exist_ok=True)
    results_path = output_directory / "phase3_baseline.csv"
    summary_path = output_directory / "phase3_baseline_summary.csv"
    results.to_csv(results_path, index=False)
    zone_summary.to_csv(summary_path, index=False)
    return results_path.resolve(), summary_path.resolve()


def main() -> None:
    """Execute a reproducible full-day baseline and print benchmark metrics."""
    results = run_baseline_day(BuildingSimulator(random_seed=42), BaselineController())
    summary = calculate_baseline_summary(results)
    zone_summary = calculate_zone_summary(results)
    print("Data source: Lightweight Development Simulator")
    print("Result classification: development")
    print("This benchmark is not official EnergyPlus savings evidence.")
    print(f"Total rows: {len(results)}")
    print(f"Unique zones: {results['zone_id'].nunique()}")
    print("Development baseline schedule:")
    print(
        f"  Occupied: {BASELINE.occupied_setpoint_c:g}°C, "
        f"{BASELINE.occupied_fan_speed_percent}% fan, "
        f"{BASELINE.occupied_ventilation} ventilation"
    )
    print(
        f"  Unoccupied: {BASELINE.unoccupied_setpoint_c:g}°C, "
        f"{BASELINE.unoccupied_fan_speed_percent}% fan, "
        f"{BASELINE.unoccupied_ventilation} ventilation"
    )
    print(f"Total energy: {summary['total_energy_kwh']:.2f} kWh")
    print(
        f"Electricity cost: {summary['total_cost_inr']:.2f} "
        f"{OPTIMIZATION.currency_code}"
    )
    print(f"Carbon emissions: {summary['total_carbon_kg']:.2f} kg CO2")
    print(f"Peak HVAC power: {summary['peak_hvac_power_kw']:.2f} kW")
    print(f"Comfort compliance: {summary['comfort_compliance_percent']:.1f}%")
    print(f"CO2 compliance: {summary['co2_compliance_percent']:.1f}%")
    print("\nZone summary:")
    print(zone_summary.to_string(index=False))
    results_path, summary_path = export_baseline_results(
        results, zone_summary, Path("results") / "development"
    )
    legacy_results_path, legacy_summary_path = export_baseline_results(
        results, zone_summary, Path("data")
    )
    print(f"\nDevelopment results CSV: {results_path}")
    print(f"Development zone summary CSV: {summary_path}")
    print(f"Compatibility results CSV: {legacy_results_path}")
    print(f"Compatibility zone summary CSV: {legacy_summary_path}")


if __name__ == "__main__":
    main()
