"""Streamlit configuration shell for EcoPilot AI Phase 1."""

import pandas as pd
import streamlit as st

from config.settings import AIR_QUALITY, BASELINE, COMFORT, HVAC, OPTIMIZATION, SIMULATION
from config.zones import ZONES


def _range_text(minimum: float, maximum: float) -> str:
    return f"{minimum:g}°C–{maximum:g}°C"


def main() -> None:
    """Render the Phase 1 configuration dashboard."""
    st.set_page_config(page_title="EcoPilot AI", page_icon="🏢", layout="wide")
    st.title("EcoPilot AI")
    st.subheader("Autonomous Smart Building Energy and Comfort Optimization")
    st.write(
        "This application will become a safe, predictive, closed-loop HVAC optimization "
        "platform. It will compare deterministic, safety-supervised decisions with a fixed "
        "baseline while balancing energy, comfort, air quality, and carbon."
    )
    st.success("Phase 1 setup is complete. The building simulator will be implemented in Phase 2.")

    duration_hours = SIMULATION.end_hour - SIMULATION.start_hour
    horizon_minutes = SIMULATION.step_minutes * SIMULATION.prediction_horizon_steps
    metrics = (
        ("Configured Zones", len(ZONES)), ("Simulation Step", f"{SIMULATION.step_minutes} minutes"),
        ("Simulation Duration", f"{duration_hours} hours"), ("Total Simulation Steps", SIMULATION.total_steps),
        ("Prediction Horizon", f"{horizon_minutes} minutes"),
        ("Occupied Comfort Range", _range_text(COMFORT.occupied_allowed_min_c, COMFORT.occupied_allowed_max_c)),
    )
    columns = st.columns(3)
    for index, (label, value) in enumerate(metrics):
        columns[index % 3].metric(label, value)

    st.header("Building Zones")
    for zone_id, zone in ZONES.items():
        with st.expander(zone["name"], expanded=True):
            st.write({
                "Zone ID": zone_id, "Area": f'{zone["area_m2"]:g} m²',
                "Maximum occupancy": zone["maximum_occupancy"],
                "Equipment heat level": zone["equipment_heat_level"].title(),
                "Initial temperature": f'{zone["initial_temperature_c"]:g}°C',
                "Initial humidity": f'{zone["initial_humidity_percent"]:g}%',
                "Initial CO2": f'{zone["initial_co2_ppm"]:g} ppm',
                "Maximum HVAC power": f'{zone["maximum_hvac_power_kw"]:g} kW',
                "Normal operating hours": f'{zone["normal_start_hour"]:02d}:00–{zone["normal_end_hour"]:02d}:00',
            })

    st.header("Comfort and Air-Quality Constraints")
    st.write({
        "Preferred occupied temperature": _range_text(COMFORT.occupied_preferred_min_c, COMFORT.occupied_preferred_max_c),
        "Allowed occupied temperature": _range_text(COMFORT.occupied_allowed_min_c, COMFORT.occupied_allowed_max_c),
        "Unoccupied temperature": _range_text(COMFORT.unoccupied_allowed_min_c, COMFORT.unoccupied_allowed_max_c),
        "Critical temperature limits": _range_text(COMFORT.critical_min_temperature_c, COMFORT.critical_max_temperature_c),
        "Normal CO2 maximum": f"{AIR_QUALITY.normal_co2_max_ppm:g} ppm",
        "Allowed CO2 maximum": f"{AIR_QUALITY.allowed_co2_max_ppm:g} ppm",
        "Warning CO2 maximum": f"{AIR_QUALITY.warning_co2_max_ppm:g} ppm",
        "Critical CO2 maximum": f"{AIR_QUALITY.critical_co2_max_ppm:g} ppm",
    })

    st.header("Baseline Controller")
    st.write({
        "Occupied setpoint": f"{BASELINE.occupied_setpoint_c:g}°C",
        "Occupied fan speed": f"{BASELINE.occupied_fan_speed_percent}%",
        "Occupied ventilation": BASELINE.occupied_ventilation.title(),
        "Unoccupied setpoint": f"{BASELINE.unoccupied_setpoint_c:g}°C",
        "Unoccupied fan speed": f"{BASELINE.unoccupied_fan_speed_percent}%",
        "Unoccupied ventilation": BASELINE.unoccupied_ventilation.title(),
    })
    st.info("The future baseline uses fixed schedules and does not react to actual occupancy.")

    st.header("Future EcoPilot Optimization Actions")
    st.caption("Configuration only — the optimizer is not implemented in Phase 1.")
    st.write("Candidate setpoints:", ", ".join(f"{v:g}°C" for v in HVAC.setpoint_candidates_c))
    st.write("Candidate fan speeds:", ", ".join(f"{v}%" for v in HVAC.fan_speed_candidates_percent))
    st.write("Candidate ventilation levels:", ", ".join(HVAC.ventilation_candidates))
    st.write("Objective weights:", {
        "Energy": OPTIMIZATION.energy_weight,
        "Comfort penalty": OPTIMIZATION.comfort_penalty_weight,
        "CO2 penalty": OPTIMIZATION.co2_penalty_weight,
        "Carbon": OPTIMIZATION.carbon_weight,
        "Control change penalty": OPTIMIZATION.control_change_penalty_weight,
    })

    st.header("Phase Status")
    phases = [
        ("Phase 1", "Setup and requirements", "Complete"),
        ("Phase 2", "Building simulator", "Not started"),
        ("Phase 3", "Baseline controller", "Not started"),
        ("Phase 4", "Prediction", "Not started"),
        ("Phase 5", "Optimization", "Not started"),
        ("Phase 6", "Safety and closed loop", "Not started"),
        ("Phase 7", "Dashboard expansion", "Not started"),
        ("Phase 8", "Metrics", "Not started"), ("Phase 9", "MCP", "Not started"),
        ("Phase 10", "LLM", "Not started"), ("Phase 11", "EnergyPlus", "Not started"),
    ]
    st.dataframe(pd.DataFrame(phases, columns=("Phase", "Focus", "Status")), hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
