"""Run and export a complete Phase 2 validation day."""

from pathlib import Path

from simulator.building import BuildingSimulator


def main() -> None:
    """Run the simulator, print validation summaries, and export CSV."""
    frame = BuildingSimulator(random_seed=42).run_full_day()
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

    output_path = Path("data") / "phase2_simulation.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    print(f"\nCSV saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
