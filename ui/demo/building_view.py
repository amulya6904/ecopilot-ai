"""Artifact-backed building and zone operations view."""

from datetime import datetime, time
from typing import Any

import pandas as pd

from ui.components import status_badge
from ui.formatting import format_demand

from .charts import filtered_line_chart
from .components import product_header, safe_page_error
from .data import (
    CONTROLLED_ZONE,
    DEMO_MODE_REPLAY,
    ArtifactLoadError,
    load_demo_context,
    load_facility_telemetry,
    load_zone_telemetry,
)


def _comfort_state(row: pd.Series) -> str:
    occupancy = pd.to_numeric(row.get("occupancy_controlled"), errors="coerce")
    temperature = pd.to_numeric(
        row.get("indoor_temperature_c_controlled"),
        errors="coerce",
    )
    if pd.isna(temperature):
        return "Telemetry unavailable"
    if pd.isna(occupancy) or occupancy <= 0:
        return "Unoccupied"
    if temperature < 22:
        return "Below configured range"
    if temperature > 25:
        return "Above configured range"
    return "Comfortable"


def _selected_timestamp(
    zones: pd.DataFrame,
    selected_date: Any,
    selected_hour: int,
) -> pd.Timestamp:
    requested = pd.Timestamp(
        datetime.combine(selected_date, time(hour=selected_hour))
    )
    available = zones["timestamp"].dropna()
    return pd.Timestamp(available.iloc[(available - requested).abs().argmin()])


def _render_overview(
    streamlit: Any,
    snapshot: pd.DataFrame,
    timestamp: pd.Timestamp,
) -> None:
    streamlit.caption(
        f"Selected timestamp · {timestamp} · verified EnergyPlus artifact replay"
    )
    with streamlit.container(horizontal=True, gap="small"):
        for _, row in snapshot.iterrows():
            zone = str(row["energyplus_zone_name"])
            controlled = zone == CONTROLLED_ZONE
            state = _comfort_state(row)
            with streamlit.container(border=True, key=f"building-zone-{zone.lower()}"):
                streamlit.caption(
                    f"{'CONTROLLED' if controlled else 'MONITORED ONLY'} · "
                    f"{row.get('zone_role_controlled', 'zone')}"
                )
                streamlit.subheader(
                    str(row.get("display_zone_name_controlled") or zone)
                )
                streamlit.caption(zone)
                temperature = row.get("indoor_temperature_c_controlled")
                occupancy = row.get("occupancy_controlled")
                setpoint = row.get("cooling_setpoint_c_controlled")
                streamlit.metric(
                    "Temperature",
                    (
                        f"{float(temperature):.2f} °C"
                        if pd.notna(temperature)
                        else "Unavailable"
                    ),
                )
                streamlit.caption(
                    "Occupancy · "
                    + (
                        f"{float(occupancy):.0f} people"
                        if pd.notna(occupancy)
                        else "Unavailable"
                    )
                )
                streamlit.caption(
                    "Cooling setpoint · "
                    + (
                        f"{float(setpoint):.1f} °C"
                        if pd.notna(setpoint) and float(setpoint) > 0
                        else "Not applicable"
                    )
                )
                status_badge(
                    streamlit,
                    state,
                    status=(
                        "verified"
                        if state == "Comfortable"
                        else "info"
                        if state == "Unoccupied"
                        else "warning"
                    ),
                )


def _render_zone_detail(
    streamlit: Any,
    row: pd.Series,
    facility_row: pd.Series,
) -> None:
    zone = str(row["energyplus_zone_name"])
    streamlit.subheader(str(row.get("display_zone_name_controlled") or zone))
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("EnergyPlus zone", zone),
            (
                "Temperature",
                (
                    f"{float(row['indoor_temperature_c_controlled']):.2f} °C"
                    if pd.notna(row.get("indoor_temperature_c_controlled"))
                    else "Unavailable"
                ),
            ),
            (
                "Occupancy",
                (
                    f"{float(row['occupancy_controlled']):.0f} people"
                    if pd.notna(row.get("occupancy_controlled"))
                    else "Unavailable"
                ),
            ),
            (
                "Cooling setpoint",
                (
                    f"{float(row['cooling_setpoint_c_controlled']):.1f} °C"
                    if pd.notna(row.get("cooling_setpoint_c_controlled"))
                    and float(row["cooling_setpoint_c_controlled"]) > 0
                    else "Not applicable"
                ),
            ),
            (
                "Relative humidity",
                (
                    f"{float(row['relative_humidity_percent_controlled']):.1f}%"
                    if pd.notna(row.get("relative_humidity_percent_controlled"))
                    else "Unavailable"
                ),
            ),
            ("Comfort state", _comfort_state(row)),
            (
                "Control authority",
                "Safety supervised" if zone == CONTROLLED_ZONE else "Monitored only",
            ),
        ):
            with streamlit.container(border=True):
                streamlit.caption(label.upper())
                streamlit.markdown(f"**{value}**")
    streamlit.caption(
        "Facility context · outdoor "
        f"{float(facility_row['outdoor_temperature_c_controlled']):.1f} °C · "
        f"demand {format_demand(facility_row['facility_demand_kw_controlled'])}"
    )
    if zone == CONTROLLED_ZONE:
        streamlit.success(
            "SPACE1-1 is the sole verified cooling-setpoint actuator target. "
            "The other zones remain monitored only."
        )


def render_building(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    product_header(
        streamlit,
        title="Building",
        subtitle=(
            "Zone conditions, occupancy, setpoints, and facility context from "
            "the latest aligned EnergyPlus comparison."
        ),
        eyebrow="Digital twin operations",
        mode=mode,
    )
    try:
        context = load_demo_context()
        zones = load_zone_telemetry()
        facility = load_facility_telemetry()
    except ArtifactLoadError as exc:
        safe_page_error(
            streamlit,
            title="Building telemetry unavailable",
            message=exc.public_message,
            next_step="Regenerate the Phase 10 comparison artifacts, then refresh.",
            diagnostics=exc.diagnostics,
        )
        return

    zone_options = zones["energyplus_zone_name"].dropna().drop_duplicates().tolist()
    controlled_rows = zones.loc[zones["energyplus_zone_name"].eq(CONTROLLED_ZONE)]
    occupied = controlled_rows.loc[
        pd.to_numeric(
            controlled_rows["occupancy_controlled"],
            errors="coerce",
        ).fillna(0)
        > 0
    ]
    default_timestamp = (
        occupied["timestamp"].max() if not occupied.empty else zones["timestamp"].max()
    )
    controls = streamlit.container(horizontal=True, vertical_alignment="bottom")
    selected_zone = controls.selectbox(
        "Zone",
        zone_options,
        index=zone_options.index(CONTROLLED_ZONE),
        key="building-zone-select",
    )
    selected_date = controls.date_input(
        "Artifact date",
        value=default_timestamp.date(),
        min_value=zones["timestamp"].min().date(),
        max_value=zones["timestamp"].max().date(),
        key="building-date",
    )
    selected_hour = controls.selectbox(
        "Hour",
        list(range(24)),
        index=int(default_timestamp.hour),
        format_func=lambda value: f"{value:02d}:00",
        key="building-hour",
    )
    timestamp = _selected_timestamp(zones, selected_date, selected_hour)
    snapshot = zones.loc[zones["timestamp"].eq(timestamp)].copy()
    selected_row = snapshot.loc[
        snapshot["energyplus_zone_name"].eq(selected_zone)
    ].iloc[0]
    facility_row = facility.iloc[
        (facility["timestamp"] - timestamp).abs().argmin()
    ]

    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("Outdoor temperature", f"{facility_row['outdoor_temperature_c_controlled']:.1f} °C"),
            ("Facility demand", f"{facility_row['facility_demand_kw_controlled']:.3f} kW"),
            (
                "Interval electricity",
                f"{facility_row['facility_electricity_kwh_controlled']:.3f} kWh",
            ),
            ("Detected zones", f"{len(snapshot)}"),
            ("Controlled zones", "1"),
        ):
            streamlit.metric(label, value, border=True)

    runtime = context.get("runtime", {}).get("summary", {})
    with streamlit.container(border=True, key="building-control-authority"):
        streamlit.caption("SPACE1-1 · VERIFIED CONTROL AUTHORITY")
        with streamlit.container(horizontal=True, gap="small"):
            for label, value in (
                ("Latest requested", runtime.get("requested_setpoint_c")),
                ("Latest approved", runtime.get("approved_setpoint_c")),
                ("Latest applied", runtime.get("applied_setpoint_c")),
                ("Latest safe setpoint", runtime.get("setpoint_after_reset_c")),
            ):
                streamlit.metric(
                    label,
                    f"{float(value):.1f} °C"
                    if isinstance(value, (int, float))
                    else "Unavailable",
                    border=True,
                )
        status_badge(
            streamlit,
            "Deterministic safety supervised · injection verified",
            status="verified",
        )

    view = streamlit.segmented_control(
        "Building view",
        ("Overview", "Zone Details", "Setpoints", "Occupancy", "Telemetry Table"),
        default="Overview",
        key="building-view",
    )
    if view == "Overview":
        _render_overview(streamlit, snapshot, timestamp)
    elif view == "Zone Details":
        _render_zone_detail(streamlit, selected_row, facility_row)
    elif view == "Setpoints":
        selected = zones.loc[zones["energyplus_zone_name"].eq(selected_zone)].copy()
        selected = selected.loc[
            selected["timestamp"].between(
                timestamp - pd.Timedelta(days=14),
                timestamp + pd.Timedelta(days=14),
            )
        ]
        filtered_line_chart(
            streamlit,
            selected,
            series={
                "cooling_setpoint_c_baseline": "Fixed-schedule baseline",
                "cooling_setpoint_c_controlled": "Safety-supervised controlled",
                "heating_setpoint_c_controlled": "Controlled heating setpoint",
            },
            y_title="Zone setpoint (°C)",
            source="Phase 10 aligned_zone_telemetry.csv",
            zero=False,
        )
        streamlit.caption(
            "Only SPACE1-1 has verified cooling-setpoint control authority."
        )
    elif view == "Occupancy":
        selected = zones.loc[zones["energyplus_zone_name"].eq(selected_zone)].copy()
        selected = selected.loc[
            selected["timestamp"].between(
                timestamp - pd.Timedelta(days=14),
                timestamp + pd.Timedelta(days=14),
            )
        ]
        filtered_line_chart(
            streamlit,
            selected,
            series={"occupancy_controlled": "EnergyPlus occupancy"},
            y_title="Occupancy (people)",
            source="EnergyPlus Zone People Occupant Count",
            zero=True,
        )
    else:
        day = zones.loc[
            zones["timestamp"].dt.date.eq(selected_date)
            & zones["energyplus_zone_name"].eq(selected_zone)
        ].copy()
        streamlit.dataframe(
            day[
                [
                    "timestamp",
                    "energyplus_zone_name",
                    "occupancy_controlled",
                    "indoor_temperature_c_controlled",
                    "cooling_setpoint_c_controlled",
                    "heating_setpoint_c_controlled",
                    "relative_humidity_percent_controlled",
                    "comfort_method_controlled",
                ]
            ],
            hide_index=True,
        )
        streamlit.caption(
            "Source · Phase 10 aligned_zone_telemetry.csv · verified artifact replay"
        )


__all__ = ["render_building"]
