"""Streamlit dashboard for EcoPilot AI Phases 1 through 8."""

import json
from pathlib import Path
import pandas as pd
import plotly.express as px

try:
    import streamlit as st
except ModuleNotFoundError:  # Allows architecture/import tests without UI extras.
    st = None  # type: ignore[assignment]

from backends import EnergyPlusBackend, get_backend_status
from config.settings import (
    AIR_QUALITY, BASELINE, COMFORT, ENERGYPLUS, HVAC, OPTIMIZATION, SIMULATION
)
from config.zones import ZONES
from controllers.baseline import BaselineController, run_baseline_day
from metrics.baseline_metrics import calculate_baseline_summary, calculate_zone_summary
from energyplus.adapter.error_parser import classify_energyplus_warning
from simulator.building import BuildingSimulator
from ui.phase5 import render_phase5
from ui.phase6 import render_phase6
from ui.phase7 import render_phase7
from ui.phase8 import phase8_complete, render_phase8
from ui.phase9 import phase9_complete, render_phase9


def _range_text(minimum: float, maximum: float) -> str:
    return f"{minimum:g}°C–{maximum:g}°C"


def _phase_table() -> pd.DataFrame:
    phase4_result = (
        st.session_state.get("phase4_result")
        if st is not None else None
    )
    phase4_status = (
        "Complete"
        if phase4_result is not None and phase4_result.success
        else "Environment dependent"
    )
    phase5_result = (
        st.session_state.get("phase5_result")
        if st is not None else None
    )
    persisted_phase5 = Path(
        "results/official/phase5_energyplus_baseline_summary.json"
    )
    phase5_complete = bool(
        phase5_result is not None and phase5_result.success
    )
    if not phase5_complete and persisted_phase5.is_file():
        try:
            stored = json.loads(persisted_phase5.read_text(encoding="utf-8"))
            phase5_complete = bool(
                stored.get("success")
                and stored.get("classification")
                == "official_energyplus_baseline"
                and stored.get("official_result") is True
                and stored.get("baseline_result") is True
            )
        except (OSError, json.JSONDecodeError):
            phase5_complete = False
    phases = [
        ("Phase 1", "Configuration and architecture foundation", "Complete"),
        ("Phase 2", "Lightweight development simulator", "Complete"),
        ("Phase 3", "Lightweight fixed baseline benchmark", "Complete"),
        ("Phase 4", "EnergyPlus integration", phase4_status),
        (
            "Phase 5",
            "Official fixed-schedule EnergyPlus baseline",
            "Complete" if phase5_complete else "Not run",
        ),
        ("Phase 6", "MCP Tool Layer for EnergyPlus and official baseline data", "Complete"),
        ("Phase 7", "Open-source LLM advisory agent over MCP", "Complete"),
        (
            "Phase 8",
            "Safe closed-loop EnergyPlus control validation",
            "Complete" if phase8_complete() else "Not run",
        ),
        (
            "Phase 9",
            "Safety, PMV, and constraints",
            "Complete" if phase9_complete() else "Not run",
        ),
        ("Phase 10", "Quantitative comparison", "Not started"),
        ("Phase 11", "Final dashboard", "Not started"),
        ("Phase 12", "Submission material", "Not started"),
    ]
    return pd.DataFrame(phases, columns=("Phase", "Focus", "Status"))


def _render_project_status() -> None:
    """Show the required target and the honest current implementation state."""

    statuses = get_backend_status()
    official_baseline = Path(
        "results/official/phase5_energyplus_baseline_summary.json"
    ).is_file()
    st.info(
        "**Project status:** EnergyPlus is the primary required final engine. "
        + (
            "The Phase 5 fixed-schedule baseline has official EnergyPlus artifacts."
            if official_baseline
            else "Lightweight results remain development-only until Phase 5 is run."
        )
    )
    columns = st.columns(3)
    columns[0].write("**Primary required engine**  \nEnergyPlus")
    columns[1].write(
        "**Current development backend**  \n"
        f"{statuses['lightweight']['label']}"
    )
    columns[2].write(
        "**EnergyPlus integration**  \n"
        + (
            "Installation detected; run not ready"
            if statuses["energyplus"]["installed"]
            else "Installation not detected"
        )
    )
    with st.expander("Integration roadmap status"):
        st.write({
            "Lightweight backend": "Available",
            "EnergyPlus backend": (
                "Installed; model/weather pending"
                if statuses["energyplus"]["installed"] else "Unavailable"
            ),
            "Official evaluation backend": "EnergyPlus required",
            "Open-source LLM": "Implemented (local Ollama; advisory only)",
            "MCP tools": "Implemented (local stdio)",
            "Closed-loop EnergyPlus control": (
                "Validated" if phase8_complete() else "Not run"
            ),
            "Current results": (
                "Official EnergyPlus baseline available"
                if official_baseline else "Development-only"
            ),
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


def render_phase4() -> None:
    """Render EnergyPlus readiness and on-demand Phase 4 batch validation."""
    st.header("Phase 4 — EnergyPlus Integration")
    st.write(
        "This phase validates the installed EnergyPlus engine, configured IDF and "
        "EPW inputs, batch execution, diagnostics, and initial EnergyPlus-derived "
        "telemetry. It does not perform AI control, optimization, actuator injection, "
        "or closed-loop operation."
    )
    backend = EnergyPlusBackend()
    status = backend.availability_status()
    cards = st.columns(4)
    cards[0].metric("Backend", backend.display_name)
    cards[1].metric("Installation", "Detected" if status.installed else "Not detected")
    cards[2].metric("Detected version", status.detected_version or "Not detected")
    cards[3].metric(
        "Simulation environment",
        "Ready" if status.ready_for_run else "Not ready",
    )
    st.subheader("Configuration")
    st.write({
        "EnergyPlus home": str(status.installation_dir or ENERGYPLUS.installation_dir),
        "Executable": str(status.executable_path or ENERGYPLUS.executable_path),
        "IDD": str(status.idd_path or ENERGYPLUS.idd_path),
        "Executable found": status.executable_found,
        "IDD found": status.idd_found,
        "IDF": str(ENERGYPLUS.base_model_path),
        "EPW": str(ENERGYPLUS.weather_file_path),
        "Model ready": status.model_exists,
        "Weather ready": status.weather_exists,
        "Full run readiness": status.ready_for_run,
    })
    if status.readiness_issues:
        st.warning("Simulation environment is not ready.")
        st.subheader("Remaining issues")
        for issue in status.readiness_issues:
            st.write(f"- {issue}")
    if not status.ready_for_run:
        st.info(
            "EnergyPlus is installed, but the simulation environment is not ready. "
            "Resolve the listed IDF, EPW, or workspace issues."
            if status.installed else
            "EnergyPlus installation was not detected. Configure ENERGYPLUS_* paths."
        )
    elif st.session_state.get("phase4_result") is None:
        st.info(
            "EnergyPlus installation, IDF model, EPW weather file, and output "
            "workspace are ready. Run the first real EnergyPlus simulation to "
            "complete Phase 4 validation."
        )
    if st.button(
        "Run EnergyPlus Simulation",
        type="primary",
        disabled=not status.ready_for_run,
        key="phase4_run",
    ):
        with st.spinner("Running EnergyPlus batch simulation..."):
            result = backend.run_simulation()
            st.session_state["phase4_result"] = result
            st.session_state["phase4_telemetry"] = backend.history_dataframe()
            st.session_state["phase4_building_telemetry"] = (
                backend.building_history_dataframe()
            )
            st.session_state["phase4_summary"] = backend.get_telemetry_summary()
            st.session_state["phase4_errors"] = backend.get_runtime_errors()
    result = st.session_state.get("phase4_result")
    if result is None:
        return
    if result.success:
        st.success("Phase 4 EnergyPlus execution validation completed successfully.")
    else:
        st.error(f"EnergyPlus validation failed: {result.failure_reason}")
    run_cards = st.columns(4)
    run_cards[0].metric("Run ID", result.run_id)
    run_cards[1].metric("Exit code", result.exit_code)
    run_cards[2].metric("Duration", f"{result.duration_seconds:.2f} s")
    run_cards[3].metric("Success", "Yes" if result.success else "No")
    st.write({
        "Warnings": result.warning_count,
        "Severe errors": result.severe_count,
        "Fatal errors": result.fatal_count,
        "Output directory": str(result.output_dir),
        "Backend": result.backend,
        "Classification": result.classification,
        "Official EnergyPlus-derived result": result.official_result,
        "AI controlled": result.ai_controlled,
        "Closed loop": result.closed_loop,
        "Optimized": result.optimized,
        "Savings result": result.savings_result,
    })
    telemetry = st.session_state.get("phase4_telemetry", pd.DataFrame())
    building_telemetry = st.session_state.get(
        "phase4_building_telemetry", pd.DataFrame()
    )
    summary = st.session_state.get("phase4_summary")
    if summary is not None:
        st.subheader("Initial EnergyPlus telemetry")
        telemetry_cards = st.columns(5)
        telemetry_cards[0].metric(
            "Facility electricity",
            (
                f"{summary.total_electricity_kwh:.2f} kWh"
                if summary.total_electricity_kwh is not None else "Unavailable"
            ),
        )
        telemetry_cards[1].metric(
            "Peak demand",
            (
                f"{summary.peak_demand_kw:.2f} kW"
                if summary.peak_demand_kw is not None else "Unavailable"
            ),
        )
        telemetry_cards[2].metric("Zones", len(summary.zones))
        telemetry_cards[3].metric("Zone rows", summary.row_count)
        telemetry_cards[4].metric("Warnings", result.warning_count)
        st.write({
            "Zone temperature available": summary.zone_temperature_available,
            "Outdoor temperature available": summary.outdoor_temperature_available,
            "Electricity available": summary.electricity_available,
            "Demand available": summary.demand_available,
            "Electricity source": summary.electricity_source_column,
            "Demand source": summary.demand_source_column,
            "Demand method": summary.demand_calculation_method,
            "Reporting frequency": summary.reporting_frequency,
        })
    if not telemetry.empty:
        st.dataframe(telemetry.head(500), hide_index=True, use_container_width=True)
        zone_chart = px.line(
            telemetry,
            x="timestamp",
            y="indoor_temperature_c",
            color="zone_name",
            title="EnergyPlus zone mean air temperatures",
        )
        st.plotly_chart(zone_chart, use_container_width=True)
    if not building_telemetry.empty:
        for value, title, label in (
            (
                "outdoor_temperature_c",
                "EnergyPlus outdoor dry-bulb temperature",
                "Temperature (°C)",
            ),
            (
                "interval_electricity_kwh",
                "Facility electricity per interval",
                "Electricity (kWh)",
            ),
            (
                "facility_demand_kw",
                "Facility electricity demand",
                "Demand (kW)",
            ),
        ):
            if value in building_telemetry and building_telemetry[value].notna().any():
                chart = px.line(
                    building_telemetry,
                    x="timestamp",
                    y=value,
                    title=title,
                    labels={value: label, "timestamp": "Time"},
                )
                st.plotly_chart(chart, use_container_width=True)
    errors = st.session_state.get("phase4_errors", [])
    warnings = [item for item in errors if item.severity == "warning"]
    if warnings:
        st.subheader("EnergyPlus warning summary")
        st.dataframe(
            pd.DataFrame([
                {
                    "classification": classify_energyplus_warning(item.message),
                    "message": item.message,
                }
                for item in warnings
            ]),
            hide_index=True,
            use_container_width=True,
        )


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
        "development simulator, and a development benchmark. Phases 4–5 provide "
        "verified EnergyPlus execution, the official fixed-schedule baseline, "
            "a bounded local MCP tool layer, and an advisory local-LLM agent."
    )
    _render_project_status()
    page = st.sidebar.radio(
        "Navigate", (
            "Phase 1 configuration",
            "Phase 2 lightweight simulator",
            "Phase 3 development baseline",
            "Phase 4 EnergyPlus integration",
            "Phase 5 official EnergyPlus baseline",
            "Phase 6 MCP tool layer",
            "Phase 7 open-source LLM agent",
            "Phase 8 safe closed-loop control",
            "Phase 9 safety, PMV, and constraints",
        )
    )
    if page == "Phase 1 configuration":
        render_phase1()
    elif page == "Phase 2 lightweight simulator":
        render_phase2()
    elif page == "Phase 3 development baseline":
        render_phase3()
    elif page == "Phase 4 EnergyPlus integration":
        render_phase4()
    elif page == "Phase 5 official EnergyPlus baseline":
        render_phase5(st)
    elif page == "Phase 6 MCP tool layer":
        render_phase6(st)
    elif page == "Phase 7 open-source LLM agent":
        render_phase7(st)
    elif page == "Phase 8 safe closed-loop control":
        render_phase8(st)
    else:
        render_phase9(st)
    st.header("Phase Status")
    st.dataframe(_phase_table(), hide_index=True, width="stretch")


if __name__ == "__main__":
    main()
