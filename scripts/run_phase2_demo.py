"""Run and export a complete Phase 2 lightweight development validation day."""

from pathlib import Path

from simulator.building import BuildingSimulator


def main() -> None:
    """Run the simulator, print validation summaries, and export CSV."""
    frame = BuildingSimulator(random_seed=42).run_full_day()
    print("Data source: Lightweight Development Simulator")
    print("Result classification: development")
    print("Final official evaluation will use EnergyPlus.")
    print("First five rows:")
    print(frame.head().to_string(index=False))
    print("\nLast five rows:")
    print(frame.tail().to_string(index=False))
    print(f"\nTotal rows: {len(frame)}")
    print(f"Unique zones: {frame['zone_id'].nunique()}")
    print("\nTotal interval energy by zone (kWh):")
    print(frame.groupby("zone_id")["interval_energy_kwh"].sum().to_string())
    print("\nIndoor temperature min/max by zone (°C):")
    print(frame.groupby("zone_id")["indoor_temperature_c"].agg(["min", "max"]).to_string())
    print("\nMaximum CO2 by zone (ppm):")
    print(frame.groupby("zone_id")["co2_ppm"].max().to_string())

    output_path = Path("results") / "development" / "phase2_simulation.csv"
    legacy_path = Path("data") / "phase2_simulation.csv"
    for path in (output_path, legacy_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    print(f"\nDevelopment CSV saved to: {output_path.resolve()}")
    print(f"Compatibility copy saved to: {legacy_path.resolve()}")


if __name__ == "__main__":
    main()
