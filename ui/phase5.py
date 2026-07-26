"""Streamlit presentation for the official Phase 5 EnergyPlus baseline."""

from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px

from config.settings import ENERGYPLUS
from energyplus.adapter.discovery import discover_energyplus
from energyplus.baseline.artifacts import write_reproducibility_report
from energyplus.baseline.manifest import calculate_sha256
from energyplus.baseline.reproducibility import compare_baseline_runs
from energyplus.baseline.runner import run_energyplus_baseline
from energyplus.baseline.settings import ENERGYPLUS_BASELINE
from .artifact_views import PROJECT_ROOT
from .formatting import project_relative


def _aggregate_zone(frame: pd.DataFrame, selection: str) -> pd.DataFrame:
    if selection == "Raw":
        return frame
    rule = "h" if selection == "Hourly" else "D"
    values = [
        column for column in (
            "indoor_temperature_c",
            "cooling_setpoint_c",
            "heating_setpoint_c",
            "occupancy",
            "relative_humidity_percent",
            "pmv",
            "ppd_percent",
            "outdoor_temperature_c",
        )
        if column in frame and frame[column].notna().any()
    ]
    return (
        frame.set_index("timestamp")
        .groupby(
            [
                pd.Grouper(freq=rule),
                "energyplus_zone_name",
                "display_zone_name",
            ],
            dropna=False,
        )[values]
        .mean()
        .reset_index()
    )


def _aggregate_facility(frame: pd.DataFrame, selection: str) -> pd.DataFrame:
    if selection in {"Raw", "Hourly"}:
        return frame
    energy = [
        column for column in frame
        if column.endswith("_electricity_kwh")
    ]
    other = [
        column for column in ("facility_demand_kw", "outdoor_temperature_c")
        if column in frame
    ]
    indexed = frame.set_index("timestamp")
    energy_frame = indexed[energy].resample("D").sum(min_count=1)
    other_frame = indexed[other].resample("D").mean()
    return energy_frame.join(other_frame).reset_index()


def _line_chart(
    st: Any,
    frame: pd.DataFrame,
    value: str,
    title: str,
    *,
    color: str | None = None,
) -> None:
    if value not in frame or not frame[value].notna().any():
        return
    chart = px.line(
        frame,
        x="timestamp",
        y=value,
        color=color,
        title=title,
    )
    st.plotly_chart(chart, width="stretch")


def _download(st: Any, label: str, path: Path, mime: str) -> None:
    if path.is_file():
        st.download_button(
            label,
            data=path.read_bytes(),
            file_name=path.name,
            mime=mime,
            key=f"phase5_download_{path.name}",
        )


def render_phase5(st: Any) -> None:
    """Render readiness, on-demand execution, metrics, charts, and downloads."""
    settings = ENERGYPLUS_BASELINE
    source = settings.resolve(settings.base_model_path)
    baseline = settings.resolve(settings.baseline_model_path)
    weather = settings.resolve(settings.weather_file_path)
    output_root = settings.resolve(settings.official_output_root)
    discovery_settings = replace(
        ENERGYPLUS,
        base_model_path=source,
        weather_file_path=weather,
        output_root=output_root,
        metadata_root=settings.resolve(settings.metadata_root),
    )
    status = discover_energyplus(discovery_settings)
    st.write(
        "This page runs the conventional fixed-schedule EnergyPlus benchmark. "
        "It provides the official reference case for future autonomous control. "
        "It is not AI-controlled, optimized, or closed-loop."
    )

    st.subheader("Baseline readiness")
    readiness = st.columns(6)
    readiness[0].metric("EnergyPlus", "Available" if status.installed else "Unavailable")
    readiness[1].metric("Source model", "Ready" if source.is_file() else "Missing")
    readiness[2].metric("Weather", "Ready" if weather.is_file() else "Missing")
    readiness[3].metric(
        "Baseline model", "Ready" if baseline.is_file() else "Build required"
    )
    readiness[4].metric(
        "Output workspace",
        "Ready" if output_root.parent.is_dir() else "Build required",
    )
    readiness[5].metric("Reporting", settings.reporting_frequency)
    if status.readiness_issues:
        st.warning("\n".join(status.readiness_issues))

    st.subheader("Model identity")
    st.write({
        "Original EnergyPlus model": source.name,
        "Derived baseline model": baseline.name,
        "Source model SHA-256": calculate_sha256(source) if source.is_file() else None,
        "Derived model SHA-256": (
            calculate_sha256(baseline) if baseline.is_file() else None
        ),
        "Weather file": weather.name,
        "EnergyPlus version": status.detected_version,
    })

    st.subheader("Zone mapping")
    mapping = pd.DataFrame([
        {
            "EnergyPlus zone name": technical,
            "Display name": display,
            "Role": settings.zone_roles[technical],
            "Included in comfort metrics": (
                "occupied" in settings.zone_roles[technical]
                and settings.zone_roles[technical] != "plenum"
            ),
        }
        for technical, display in settings.zone_display_names.items()
    ])
    st.dataframe(mapping, hide_index=True, width="stretch")

    st.subheader("Frozen baseline policy")
    policy = pd.DataFrame([
        ("Occupied start", f"{settings.occupied_start_hour:02d}:00"),
        ("Occupied end", f"{settings.occupied_end_hour:02d}:00"),
        ("Occupied cooling setpoint", f"{settings.occupied_cooling_setpoint_c:g}°C"),
        ("Unoccupied cooling setpoint", f"{settings.unoccupied_cooling_setpoint_c:g}°C"),
        ("Occupied heating setpoint", f"{settings.occupied_heating_setpoint_c:g}°C"),
        ("Unoccupied heating setpoint", f"{settings.unoccupied_heating_setpoint_c:g}°C"),
        (
            "Occupied comfort range",
            f"{settings.occupied_temperature_min_c:g}–"
            f"{settings.occupied_temperature_max_c:g}°C",
        ),
        ("PMV range", f"{settings.pmv_min:g} to {settings.pmv_max:g}"),
    ], columns=["Policy field", "Frozen value"])
    st.dataframe(policy, hide_index=True, width="stretch")

    st.subheader("Classification")
    st.info(
        "**Backend:** EnergyPlus · **Classification:** Official EnergyPlus Baseline · "
        "**Official result:** Yes · **Baseline result:** Yes · "
        "**AI controlled:** No · **Closed loop:** No · **Optimized:** No · "
        "**Savings result:** No"
    )
    verify = st.checkbox(
        "Verify reproducibility with second run",
        value=False,
        key="phase5_verify_reproducibility",
    )
    st.caption(
        "Expected duration: approximately 1–3 minutes; a reproducibility "
        "repeat takes longer."
    )
    if st.button(
        "Run Official EnergyPlus Baseline",
        type="primary",
        disabled=not status.ready_for_run,
        key="phase5_run",
    ):
        with st.spinner("Running the official annual EnergyPlus baseline..."):
            first = run_energyplus_baseline(settings)
            st.session_state["phase5_result"] = first
            if verify and first.success:
                second = run_energyplus_baseline(settings)
                report = compare_baseline_runs(
                    first, second, settings.reproducibility_tolerance
                )
                report_path = write_reproducibility_report(
                    settings.resolve(settings.official_results_root),
                    asdict(report),
                )
                first.reproducibility_status = report
                first.artifact_paths["reproducibility"] = report_path
                st.session_state["phase5_reproducibility"] = report

    result = st.session_state.get("phase5_result")
    if result is None:
        st.info("Run control is explicit; normal page rerenders do not execute EnergyPlus.")
        return
    if not result.success:
        st.error(f"Official baseline failed: {result.failure_reason}")
        return
    st.success("Phase 5 official EnergyPlus baseline completed successfully.")
    summary = result.baseline_summary
    cards = st.columns(4)
    card_values = (
        ("Facility electricity", f"{summary['total_facility_electricity_kwh']:.2f} kWh"),
        ("Peak demand", f"{summary['peak_facility_demand_kw']:.2f} kW"),
        ("Average demand", f"{summary['average_facility_demand_kw']:.2f} kW"),
        (
            "Temperature compliance",
            f"{summary['temperature_compliance_percent']:.2f}%",
        ),
        (
            "PMV compliance",
            (
                f"{summary['pmv_compliance_percent']:.2f}%"
                if summary["pmv_compliance_percent"] is not None else "Unavailable"
            ),
        ),
        ("Thermostat adherence", f"{summary['thermostat_adherence_percent']:.2f}%"),
        ("Occupied zones", summary["occupied_zone_count"]),
        ("Warnings", summary["warning_count"]),
    )
    for index, (label, value) in enumerate(card_values):
        cards[index % 4].metric(label, value)

    zone = result.zone_telemetry.copy()
    facility = result.facility_telemetry.copy()
    zone["timestamp"] = pd.to_datetime(zone["timestamp"])
    facility["timestamp"] = pd.to_datetime(facility["timestamp"])
    st.caption(
        "EnergyPlus timestamps are hourly interval ends represented with reference "
        "year 2000 because the source CSV has no year."
    )
    controls = st.columns(3)
    aggregation = controls[0].selectbox(
        "Aggregation", ("Hourly", "Daily", "Raw"), index=0
    )
    available_zones = zone["display_zone_name"].drop_duplicates().tolist()
    selected_zones = controls[1].multiselect(
        "Zones", available_zones, default=available_zones
    )
    min_date = zone["timestamp"].min().date()
    max_date = zone["timestamp"].max().date()
    selected_dates = controls[2].date_input(
        "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start = pd.Timestamp(selected_dates[0])
        end = pd.Timestamp(selected_dates[1]) + pd.Timedelta(days=1)
        zone = zone[
            (zone["timestamp"] >= start)
            & (zone["timestamp"] < end)
            & zone["display_zone_name"].isin(selected_zones)
        ]
        facility = facility[
            (facility["timestamp"] >= start) & (facility["timestamp"] < end)
        ]
    zone_chart = _aggregate_zone(zone, aggregation)
    facility_chart = _aggregate_facility(facility, aggregation)
    _line_chart(
        st, zone_chart, "indoor_temperature_c",
        "Zone temperature by display name", color="display_zone_name"
    )
    _line_chart(
        st, zone_chart, "cooling_setpoint_c",
        "Cooling setpoint by display name", color="display_zone_name"
    )
    _line_chart(
        st, zone_chart, "heating_setpoint_c",
        "Heating setpoint by display name", color="display_zone_name"
    )
    _line_chart(
        st, zone_chart, "occupancy",
        "EnergyPlus people occupancy by display name", color="display_zone_name"
    )
    _line_chart(
        st, facility_chart, "outdoor_temperature_c",
        "Outdoor dry-bulb temperature"
    )
    _line_chart(
        st, facility_chart, "facility_electricity_kwh",
        "Facility electricity per interval"
    )
    _line_chart(
        st, facility_chart, "facility_demand_kw", "Facility demand"
    )
    _line_chart(
        st, zone_chart, "pmv", "Fanger PMV", color="display_zone_name"
    )
    _line_chart(
        st, zone_chart, "ppd_percent", "Fanger PPD", color="display_zone_name"
    )

    st.subheader("Schedule-boundary validation")
    st.dataframe(result.schedule_boundary_table.head(500), hide_index=True, width="stretch")
    st.subheader("Zone summary")
    st.dataframe(result.zone_summary, hide_index=True, width="stretch")
    st.subheader("Raw telemetry previews")
    st.dataframe(result.zone_telemetry.head(500), hide_index=True, width="stretch")
    st.dataframe(result.facility_telemetry.head(500), hide_index=True, width="stretch")
    st.subheader("Warnings and errors")
    error_path = result.artifact_paths.get("errors")
    if error_path and error_path.is_file():
        st.json(json.loads(error_path.read_text(encoding="utf-8")))
    st.subheader("Manifest")
    st.json(result.manifest, expanded=False)
    report = st.session_state.get("phase5_reproducibility")
    if report is not None:
        st.subheader("Reproducibility")
        st.json(asdict(report))
    st.subheader("Official artifacts")
    artifact_table = pd.DataFrame([
        {
            "Artifact": name,
            "Path": project_relative(path, PROJECT_ROOT),
            "Exists": path.is_file(),
        }
        for name, path in result.artifact_paths.items()
    ])
    st.dataframe(artifact_table, hide_index=True, width="stretch")
    download_columns = st.columns(4)
    for index, (name, path) in enumerate(result.artifact_paths.items()):
        with download_columns[index % 4]:
            _download(
                st,
                f"Download {name.replace('_', ' ')}",
                path,
                "text/csv" if path.suffix == ".csv" else "application/json",
            )


__all__ = ["render_phase5"]
