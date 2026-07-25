"""Streamlit dashboard for EcoPilot AI Phases 1 through 3."""

import pandas as pd
import plotly.express as px

try:
    import streamlit as st
except ModuleNotFoundError:  # Allows architecture/import tests without UI extras.
    st = None  # type: ignore[assignment]

from backends import get_backend_status
from config.settings import AIR_QUALITY, BASELINE, COMFORT, HVAC, OPTIMIZATION, SIMULATION
from config.zones import ZONES
from controllers.baseline import BaselineController, run_baseline_day
from metrics.baseline_metrics import calculate_baseline_summary, calculate_zone_summary
from simulator.building import BuildingSimulator


def _range_text(minimum: float, maximum: float) -> str:
    return f"{minimum:g}°C–{maximum:g}°C"


def _phase_table() -> pd.DataFrame:
    phases = [
        ("Phase 1", "Configuration and architecture foundation", "Complete"),
        ("Phase 2", "Lightweight development simulator", "Complete"),
        ("Phase 3", "Lightweight fixed baseline benchmark", "Complete"),
        ("Phase 4", "EnergyPlus integration", "Not started"),
        ("Phase 5", "EnergyPlus baseline", "Not started"),
        ("Phase 6", "MCP tools", "Not started"),
        ("Phase 7", "Open-source LLM agent", "Not started"),
        ("Phase 8", "Closed-loop EnergyPlus execution", "Not started"),
        ("Phase 9", "Safety, PMV, and constraints", "Not started"),
        ("Phase 10", "Quantitative comparison", "Not started"),
        ("Phase 11", "Final dashboard", "Not started"),
        ("Phase 12", "Submission material", "Not started"),
    ]
    return pd.DataFrame(phases, columns=("Phase", "Focus", "Status"))


def _render_project_status() -> None:
    """Show the required target and the honest current implementation state."""

    statuses = get_backend_status()
    st.info(
        "**Project status:** EnergyPlus is the primary required final engine. "
        "Current results are development-only."
    )
    columns = st.columns(3)
    columns[0].write("**Primary required engine**  \nEnergyPlus")
    columns[1].write(
        "**Current development backend**  \n"
        f"{statuses['lightweight']['label']}"
    )
    columns[2].write("**EnergyPlus integration**  \nNot started")
    with st.expander("Integration roadmap status"):
        st.write({
            "Lightweight backend": "Available",
            "EnergyPlus backend": "Not connected",
            "Official evaluation backend": "EnergyPlus required",
            "Open-source LLM": "Not started",
            "MCP tools": "Not started",
            "Closed-loop EnergyPlus control": "Not started",
            "Current results": "Development-only",
        })


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
        "These settings drive the implemented Phase 3 development benchmark. "
        "The official baseline will be generated with EnergyPlus."
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
    st.header("Phase 2 — Lightweight Development Simulator")
    st.write("**Data source:** Lightweight Development Simulator")
    st.write(
        "This lightweight development digital twin models weather, occupancy, temperature, "
        "humidity, CO2, and HVAC energy for three zones at five-minute intervals."
    )
    st.info(
        "This simulator validates data flow, controls, metrics and UI behavior. "
        "Final official evaluation will use EnergyPlus."
    )
    status_columns = st.columns(3)
    status_columns[0].metric("Lightweight backend", "Available")
    status_columns[1].metric("EnergyPlus backend", "Not connected")
    status_columns[2].metric("Official evaluation backend", "EnergyPlus required")
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
    st.success("Phase 2 development validation run complete.")

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


def _plot_zone_line(
    frame: pd.DataFrame, value: str, title: str, y_label: str
) -> None:
    figure = px.line(
        frame, x="timestamp", y=value, color="zone_id",
        title=title, labels={value: y_label, "timestamp": "Time", "zone_id": "Zone"},
    )
    st.plotly_chart(figure, use_container_width=True)


def render_phase3() -> None:
    """Render the conventional fixed-schedule baseline benchmark."""
    st.header("Phase 3 — Fixed Baseline Controller")
    st.write("**Data source:** Lightweight Development Simulator")
    st.warning(
        "This is a development benchmark. Final baseline savings claims must use "
        "EnergyPlus under identical IDF and EPW conditions."
    )
    st.write(
        "This page runs the lightweight simulator's conventional fixed-schedule "
        "HVAC development benchmark. "
        "It does not use prediction, actual occupancy awareness, or optimization."
    )
    heat_wave = st.checkbox("Heat Wave Scenario", value=False, key="phase3_heat_wave")
    seed = int(st.number_input(
        "Random seed", min_value=0, value=42, step=1, key="phase3_seed"
    ))
    scenario_key = f"phase3_results_{seed}_{heat_wave}"
    if st.button("Run Baseline Simulation", type="primary"):
        with st.spinner("Running fixed-schedule baseline..."):
            results = run_baseline_day(
                BuildingSimulator(random_seed=seed, heat_wave=heat_wave),
                BaselineController(),
            )
            st.session_state[scenario_key] = (
                results,
                calculate_baseline_summary(results),
                calculate_zone_summary(results),
            )
    stored = st.session_state.get(scenario_key)
    if stored is None:
        st.info("Press Run Baseline Simulation to create this benchmark scenario.")
        return
    results, summary, zone_summary = stored
    st.success("Development baseline simulation completed successfully.")

    cards = st.columns(3)
    cards[0].metric("Development baseline energy", f"{summary['total_energy_kwh']:.2f} kWh")
    cards[1].metric("Electricity cost", f"{summary['total_cost_inr']:.2f} INR")
    cards[2].metric("Carbon emissions", f"{summary['total_carbon_kg']:.2f} kg CO2")
    cards[0].metric("Peak HVAC power", f"{summary['peak_hvac_power_kw']:.2f} kW")
    cards[1].metric("Comfort compliance", f"{summary['comfort_compliance_percent']:.1f}%")
    cards[2].metric("CO2 compliance", f"{summary['co2_compliance_percent']:.1f}%")

    st.subheader("Development baseline schedule")
    schedule = pd.DataFrame([
        {
            "Schedule": "Occupied", "Setpoint": f"{BASELINE.occupied_setpoint_c:g}°C",
            "Fan speed": f"{BASELINE.occupied_fan_speed_percent}%",
            "Ventilation": BASELINE.occupied_ventilation,
        },
        {
            "Schedule": "Unoccupied", "Setpoint": f"{BASELINE.unoccupied_setpoint_c:g}°C",
            "Fan speed": f"{BASELINE.unoccupied_fan_speed_percent}%",
            "Ventilation": BASELINE.unoccupied_ventilation,
        },
    ])
    st.dataframe(schedule, hide_index=True, use_container_width=True)

    _plot_zone_line(results, "hvac_setpoint_c", "HVAC setpoint by zone", "Setpoint (°C)")
    _plot_zone_line(results, "fan_speed_percent", "Fan speed by zone", "Fan speed (%)")
    _plot_zone_line(results, "indoor_temperature_c", "Indoor temperature by zone", "Temperature (°C)")
    _plot_zone_line(results, "co2_ppm", "CO2 by zone", "CO2 (ppm)")
    _plot_zone_line(results, "interval_energy_kwh", "Interval energy by zone", "Energy (kWh)")

    intervals = results.assign(
        interval_cost_inr=(
            results["interval_energy_kwh"] * results["electricity_price_per_kwh"]
        ),
        interval_carbon_kg=(
            results["interval_energy_kwh"]
            * results["carbon_intensity_g_per_kwh"] / 1000
        ),
    )
    by_time = intervals.groupby("timestamp", as_index=False)[
        ["interval_energy_kwh", "interval_cost_inr", "interval_carbon_kg"]
    ].sum()
    by_time["cumulative_energy_kwh"] = by_time["interval_energy_kwh"].cumsum()
    by_time["cumulative_cost_inr"] = by_time["interval_cost_inr"].cumsum()
    by_time["cumulative_carbon_kg"] = by_time["interval_carbon_kg"].cumsum()
    for value, title, label in (
        ("cumulative_energy_kwh", "Cumulative building energy", "Energy (kWh)"),
        ("cumulative_cost_inr", "Cumulative electricity cost", "Cost (INR)"),
        ("cumulative_carbon_kg", "Cumulative carbon emissions", "Emissions (kg CO2)"),
    ):
        figure = px.line(
            by_time, x="timestamp", y=value, title=title,
            labels={"timestamp": "Time", value: label},
        )
        st.plotly_chart(figure, use_container_width=True)
    energy_bar = px.bar(
        zone_summary, x="zone_name", y="total_energy_kwh",
        title="Total energy by zone",
        labels={"zone_name": "Zone", "total_energy_kwh": "Energy (kWh)"},
    )
    st.plotly_chart(energy_bar, use_container_width=True)

    st.subheader("Latest zone states")
    latest = results.sort_values("timestamp").groupby("zone_id", as_index=False).tail(1)
    st.dataframe(latest.round(2), hide_index=True, use_container_width=True)
    st.subheader("Zone-wise development baseline summary")
    st.dataframe(zone_summary.round(2), hide_index=True, use_container_width=True)
    st.subheader("Schedule-boundary samples")
    boundary = results[
        results["timestamp"].dt.strftime("%H:%M").isin(["08:00", "09:00", "18:00"])
    ][["timestamp", "zone_id", "hvac_setpoint_c", "fan_speed_percent", "ventilation_level"]]
    st.dataframe(boundary, hide_index=True, use_container_width=True)

    first, second = st.columns(2)
    first.download_button(
        "Download full baseline CSV",
        results.to_csv(index=False).encode("utf-8"),
        "ecopilot_phase3_baseline.csv", "text/csv",
    )
    second.download_button(
        "Download zone summary CSV",
        zone_summary.to_csv(index=False).encode("utf-8"),
        "ecopilot_phase3_baseline_summary.csv", "text/csv",
    )
    st.subheader("Future official EnergyPlus metrics")
    st.caption("Roadmap only — unavailable values are not represented as zero.")
    st.write({
        "EnergyPlus total electricity": "Not available",
        "Peak demand": "Development-derived only; official value not available",
        "PMV compliance": "Not available",
        "EnergyPlus runtime errors": "Not available",
        "EnergyPlus baseline IDF": "Not connected",
        "Modified runtime IDFs": "Not implemented",
    })


def main() -> None:
    """Render the EcoPilot AI dashboard."""
    if st is None:
        raise RuntimeError(
            "Streamlit is required to launch the dashboard. "
            "Install the dependencies from requirements.txt."
        )
    st.set_page_config(page_title="EcoPilot AI", page_icon="🏢", layout="wide")
    st.title("EcoPilot AI")
    st.subheader("Autonomous Smart Building Energy and Comfort Optimization")
    st.write(
        "EcoPilot AI is being developed as a safe, predictive HVAC platform. "
        "Phases 1–3 provide validated configuration, a repeatable lightweight "
        "development simulator, and a development benchmark. EnergyPlus is required "
        "for the final baseline and closed-loop evaluation."
    )
    _render_project_status()
    page = st.sidebar.radio(
        "Navigate", (
            "Phase 1 configuration",
            "Phase 2 lightweight simulator",
            "Phase 3 development baseline",
        )
    )
    if page == "Phase 1 configuration":
        render_phase1()
    elif page == "Phase 2 lightweight simulator":
        render_phase2()
    else:
        render_phase3()
    st.header("Phase Status")
    st.dataframe(_phase_table(), hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
