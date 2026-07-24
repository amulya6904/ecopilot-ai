"""Streamlit dashboard for EcoPilot AI Phases 1 and 2."""

import pandas as pd
import streamlit as st

from config.settings import AIR_QUALITY, BASELINE, COMFORT, HVAC, OPTIMIZATION, SIMULATION
from config.zones import ZONES
from simulator.building import BuildingSimulator


def _range_text(minimum: float, maximum: float) -> str:
    return f"{minimum:g}°C–{maximum:g}°C"


def _phase_table() -> pd.DataFrame:
    phases = [
        ("Phase 1", "Setup and requirements", "Complete"),
        ("Phase 2", "Building simulator", "Complete"),
        ("Phase 3", "Baseline controller", "Not started"),
        ("Phase 4", "Prediction", "Not started"),
        ("Phase 5", "Optimization", "Not started"),
        ("Phase 6", "Safety and closed loop", "Not started"),
        ("Phase 7", "Dashboard expansion", "Not started"),
        ("Phase 8", "Metrics", "Not started"),
        ("Phase 9", "MCP", "Not started"),
        ("Phase 10", "LLM", "Not started"),
        ("Phase 11", "EnergyPlus", "Not started"),
    ]
    return pd.DataFrame(phases, columns=("Phase", "Focus", "Status"))


def render_phase1() -> None:
    """Render the frozen Phase 1 configuration."""
    st.header("Phase 1 — Configuration")
    st.success("Phase 1 setup and requirement freezing are complete.")
    duration_hours = SIMULATION.end_hour - SIMULATION.start_hour
    horizon_minutes = SIMULATION.step_minutes * SIMULATION.prediction_horizon_steps
    metrics = (
        ("Configured Zones", len(ZONES)),
        ("Simulation Step", f"{SIMULATION.step_minutes} minutes"),
        ("Simulation Duration", f"{duration_hours} hours"),
        ("Total Simulation Steps", SIMULATION.total_steps),
        ("Prediction Horizon", f"{horizon_minutes} minutes"),
        ("Occupied Comfort Range", _range_text(
            COMFORT.occupied_allowed_min_c, COMFORT.occupied_allowed_max_c
        )),
    )
    columns = st.columns(3)
    for index, (label, value) in enumerate(metrics):
        columns[index % 3].metric(label, value)

    st.header("Building Zones")
    for zone_id, zone in ZONES.items():
        with st.expander(zone["name"], expanded=True):
            st.write({
                "Zone ID": zone_id,
                "Area": f'{zone["area_m2"]:g} m²',
                "Maximum occupancy": zone["maximum_occupancy"],
                "Equipment heat level": zone["equipment_heat_level"].title(),
                "Initial temperature": f'{zone["initial_temperature_c"]:g}°C',
                "Initial humidity": f'{zone["initial_humidity_percent"]:g}%',
                "Initial CO2": f'{zone["initial_co2_ppm"]:g} ppm',
                "Maximum HVAC power": f'{zone["maximum_hvac_power_kw"]:g} kW',
                "Normal operating hours": (
                    f'{zone["normal_start_hour"]:02d}:00–'
                    f'{zone["normal_end_hour"]:02d}:00'
                ),
            })

    st.header("Comfort and Air-Quality Constraints")
    st.write({
        "Preferred occupied temperature": _range_text(
            COMFORT.occupied_preferred_min_c, COMFORT.occupied_preferred_max_c
        ),
        "Allowed occupied temperature": _range_text(
            COMFORT.occupied_allowed_min_c, COMFORT.occupied_allowed_max_c
        ),
        "Unoccupied temperature": _range_text(
            COMFORT.unoccupied_allowed_min_c, COMFORT.unoccupied_allowed_max_c
        ),
        "Critical temperature limits": _range_text(
            COMFORT.critical_min_temperature_c,
            COMFORT.critical_max_temperature_c,
        ),
        "Normal CO2 maximum": f"{AIR_QUALITY.normal_co2_max_ppm:g} ppm",
        "Allowed CO2 maximum": f"{AIR_QUALITY.allowed_co2_max_ppm:g} ppm",
        "Warning CO2 maximum": f"{AIR_QUALITY.warning_co2_max_ppm:g} ppm",
        "Critical CO2 maximum": f"{AIR_QUALITY.critical_co2_max_ppm:g} ppm",
    })

    st.header("Baseline Controller Configuration")
    st.write({
        "Occupied setpoint": f"{BASELINE.occupied_setpoint_c:g}°C",
        "Occupied fan speed": f"{BASELINE.occupied_fan_speed_percent}%",
        "Occupied ventilation": BASELINE.occupied_ventilation.title(),
        "Unoccupied setpoint": f"{BASELINE.unoccupied_setpoint_c:g}°C",
        "Unoccupied fan speed": f"{BASELINE.unoccupied_fan_speed_percent}%",
        "Unoccupied ventilation": BASELINE.unoccupied_ventilation.title(),
    })
    st.info(
        "This is configuration only. The Phase 3 baseline controller is not implemented."
    )

    st.header("Future EcoPilot Optimization Actions")
    st.caption("Configuration only — no optimizer is implemented.")
    st.write("Candidate setpoints:", ", ".join(
        f"{value:g}°C" for value in HVAC.setpoint_candidates_c
    ))
    st.write("Candidate fan speeds:", ", ".join(
        f"{value}%" for value in HVAC.fan_speed_candidates_percent
    ))
    st.write("Candidate ventilation levels:", ", ".join(HVAC.ventilation_candidates))
    st.write("Objective weights:", {
        "Energy": OPTIMIZATION.energy_weight,
        "Comfort penalty": OPTIMIZATION.comfort_penalty_weight,
        "CO2 penalty": OPTIMIZATION.co2_penalty_weight,
        "Carbon": OPTIMIZATION.carbon_weight,
        "Control change penalty": OPTIMIZATION.control_change_penalty_weight,
    })


def _chart(frame: pd.DataFrame, value: str, title: str) -> None:
    st.subheader(title)
    chart_data = frame.pivot(index="timestamp", columns="zone_id", values=value)
    st.line_chart(chart_data, use_container_width=True)


def render_phase2() -> None:
    """Render an on-demand full-day simulator validation."""
    st.header("Phase 2 — Building Simulator")
    st.write(
        "This lightweight digital twin models weather, occupancy, temperature, "
        "humidity, CO2, and HVAC energy for three zones at five-minute intervals."
    )
    heat_wave = st.checkbox("Heat Wave Scenario", value=False)
    scenario_key = f"phase2_frame_{heat_wave}"
    if st.button("Run Full-Day Simulation", type="primary"):
        with st.spinner("Running Phase 2 validation run..."):
            st.session_state[scenario_key] = BuildingSimulator(
                random_seed=42, heat_wave=heat_wave
            ).run_full_day()

    frame = st.session_state.get(scenario_key)
    if frame is None:
        st.info(
            "Select the scenario and run a Phase 2 validation run. "
            "The simulator uses the fixed Default HVAC action."
        )
        return

    total_energy = frame["interval_energy_kwh"].sum()
    columns = st.columns(4)
    columns[0].metric("Total rows", len(frame))
    columns[1].metric("Total zones", frame["zone_id"].nunique())
    columns[2].metric(
        "Total simulated hours", SIMULATION.end_hour - SIMULATION.start_hour
    )
    columns[3].metric(
        "Simulation energy under fixed Phase 2 test actions",
        f"{total_energy:.2f} kWh",
    )
    st.success("Phase 2 validation run complete. Phase 3 is not started.")

    st.subheader("Latest zone states")
    latest = frame.sort_values("timestamp").groupby("zone_id", as_index=False).tail(1)
    st.dataframe(latest, hide_index=True, use_container_width=True)
    _chart(frame, "indoor_temperature_c", "Indoor temperature by zone")
    _chart(frame, "occupancy", "Occupancy by zone")
    _chart(frame, "co2_ppm", "CO2 by zone")
    _chart(frame, "interval_energy_kwh", "Interval energy by zone")
    st.download_button(
        "Download Phase 2 CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name="phase2_simulation.csv",
        mime="text/csv",
    )


def main() -> None:
    """Render the EcoPilot AI dashboard."""
    st.set_page_config(page_title="EcoPilot AI", page_icon="🏢", layout="wide")
    st.title("EcoPilot AI")
    st.subheader("Autonomous Smart Building Energy and Comfort Optimization")
    st.write(
        "EcoPilot AI is being developed as a safe, predictive HVAC platform. "
        "Phases 1 and 2 provide validated configuration and a repeatable simulator; "
        "controllers, optimization, and closed-loop operation are not implemented."
    )
    page = st.sidebar.radio(
        "Navigate", ("Phase 1 configuration", "Phase 2 simulator validation")
    )
    if page == "Phase 1 configuration":
        render_phase1()
    else:
        render_phase2()
    st.header("Phase Status")
    st.dataframe(_phase_table(), hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
