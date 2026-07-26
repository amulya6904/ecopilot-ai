"""Filtered Phase 12 analytics over immutable Phase 10 evidence."""

from typing import Any

import pandas as pd

from ui.charts import (
    action_setpoint_chart,
    fallback_timeline_chart,
    requested_approved_chart,
    safety_outcome_chart,
)
from ui.formatting import (
    format_carbon,
    format_comfort,
    format_cost,
    format_demand,
    format_energy,
    format_percent,
)

from .charts import (
    comfort_chart,
    comparison_bar_chart,
    decision_timeline_chart,
    filtered_line_chart,
)
from .components import product_header, safe_page_error
from .data import (
    CONTROLLED_ZONE,
    DEMO_MODE_REPLAY,
    ArtifactLoadError,
    load_comparison_csv,
    load_demo_context,
)


def _timestamp(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce")
    return result


def _filter_dates(
    frame: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    values = _timestamp(frame)
    return values.loc[values["timestamp"].between(start, end)].copy()


def _aggregate(
    frame: pd.DataFrame,
    aggregation: str,
    *,
    cumulative: tuple[str, ...] = (),
    method: str = "sum",
) -> pd.DataFrame:
    if frame.empty or aggregation == "Hourly":
        return frame.copy()
    frequency = "D" if aggregation == "Daily" else "MS"
    values = frame.copy().set_index("timestamp")
    numeric = values.select_dtypes(include="number").columns
    sums = [column for column in numeric if column not in cumulative]
    if method == "mean":
        aggregated = values[sums].resample(frequency).mean()
    else:
        aggregated = values[sums].resample(frequency).sum(min_count=1)
    for column in cumulative:
        if column in values:
            aggregated[column] = values[column].resample(frequency).last()
    return aggregated.reset_index()


def _calendar_action_markers(
    actions: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    if actions.empty:
        return actions
    markers = _timestamp(actions)
    markers["timestamp"] = markers["timestamp"].map(
        lambda value: (
            value.replace(year=start.year, tzinfo=None)
            if pd.notna(value)
            else value
        )
    )
    return markers.loc[markers["timestamp"].between(start, end)].copy()


def _render_summary(streamlit: Any, summary: dict[str, Any]) -> None:
    streamlit.subheader("Full-year summary")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value, note in (
            (
                "Baseline energy",
                format_energy(summary["baseline_energy_kwh"]),
                "Official EnergyPlus",
            ),
            (
                "Controlled energy",
                format_energy(summary["controlled_energy_kwh"]),
                "Official EnergyPlus",
            ),
            (
                "Energy saved",
                format_energy(summary["energy_reduction_kwh"], compact=True),
                format_percent(summary["energy_reduction_percent"], 4),
            ),
            (
                "Comfort change",
                f"{summary['comfort_metrics']['comfort_change_percent_points']:+.3f} pp",
                "Occupied-temperature proxy",
            ),
            (
                "Peak demand",
                format_demand(summary["controlled_peak_demand_kw"]),
                "Essentially unchanged",
            ),
            (
                "Cost reduction",
                format_cost(
                    summary["cost_metrics"]["absolute_cost_reduction"],
                    summary["cost_metrics"]["currency"],
                ),
                "Derived assumption",
            ),
            (
                "Carbon reduction",
                format_carbon(
                    summary["carbon_metrics"]["absolute_carbon_reduction_kg"]
                ),
                "Derived assumption",
            ),
        ):
            streamlit.metric(label, value, help=note, border=True)


def _energy_view(
    streamlit: Any,
    context: dict[str, Any],
    energy: pd.DataFrame,
    demand: pd.DataFrame,
    facility: pd.DataFrame,
    actions: pd.DataFrame,
    visibility: list[str],
    aggregation: str,
) -> None:
    summary = context["summary"]
    energy_series = {}
    interval_series = {}
    demand_series = {}
    if "Baseline" in visibility:
        energy_series["baseline_cumulative_energy_kwh"] = "Fixed-schedule baseline"
        interval_series["baseline_energy_kwh"] = "Fixed-schedule baseline"
        demand_series["baseline_demand_kw"] = "Fixed-schedule baseline"
    if "Controlled" in visibility:
        energy_series[
            "controlled_cumulative_energy_kwh"
        ] = "Safety-supervised controlled"
        interval_series["controlled_energy_kwh"] = "Safety-supervised controlled"
        demand_series["controlled_demand_kw"] = "Safety-supervised controlled"

    streamlit.subheader("Cumulative Facility Electricity")
    filtered_line_chart(
        streamlit,
        _aggregate(
            energy,
            aggregation,
            cumulative=(
                "baseline_cumulative_energy_kwh",
                "controlled_cumulative_energy_kwh",
                "cumulative_energy_reduction_kwh",
            ),
        ),
        series=energy_series,
        y_title="Cumulative facility electricity (kWh)",
        source="Phase 10 energy_comparison.csv",
        zero=False,
        action_markers=actions,
    )
    streamlit.metric(
        "Difference",
        f"−{format_energy(summary['energy_reduction_kwh'], compact=True)}",
        help="Verified annual controlled minus baseline facility electricity",
        border=True,
    )
    streamlit.subheader(f"{aggregation} Facility Electricity")
    filtered_line_chart(
        streamlit,
        _aggregate(energy, aggregation),
        series=interval_series,
        y_title=f"{aggregation.lower()} facility electricity (kWh)",
        source="Phase 10 energy_comparison.csv",
        zero=True,
        action_markers=actions,
    )
    streamlit.subheader("Facility Demand Profile")
    filtered_line_chart(
        streamlit,
        _aggregate(demand, aggregation, method="mean"),
        series=demand_series,
        y_title="Facility demand (kW)",
        source="Phase 10 demand_comparison.csv",
        zero=True,
        action_markers=actions,
    )

    components = summary["energy_components"]
    component_rows = []
    for metric, label in (
        ("cooling_energy_kwh", "Cooling electricity"),
        ("fan_energy_kwh", "Fan electricity"),
        ("heating_energy_kwh", "Heating electricity"),
        ("energy_per_occupied_hour_kwh", "Energy / occupied hour"),
    ):
        component_rows.extend(
            [
                {
                    "metric": label,
                    "run": "Fixed-schedule baseline",
                    "value": components["baseline"][metric],
                },
                {
                    "metric": label,
                    "run": "Safety-supervised controlled",
                    "value": components["controlled"][metric],
                },
            ]
        )
    streamlit.subheader("Energy-component comparison")
    comparison_bar_chart(
        streamlit,
        component_rows,
        category="metric",
        value="value",
        series="run",
        y_title="Energy (kWh)",
        source="Phase 10 final_summary.json energy_components",
    )
    streamlit.dataframe(
        [
            ("Facility electricity", "Electricity:Facility", "kWh", "Available"),
            ("Cooling electricity", "Cooling:Electricity", "kWh", "Available"),
            ("Fan electricity", "Fans:Electricity", "kWh", "Available"),
            ("Heating electricity", "Heating:Electricity", "kWh", "Available"),
            (
                "Energy per occupied hour",
                "Facility electricity ÷ occupied hours",
                "kWh/h",
                "Derived",
            ),
        ],
        column_config={
            0: "Displayed metric",
            1: "EnergyPlus meter or source column",
            2: "Unit",
            3: "Availability",
        },
        hide_index=True,
    )
    streamlit.caption(
        "Fan electricity is labelled explicitly; it is not presented as "
        "whole-HVAC electricity."
    )


def _comfort_view(
    streamlit: Any,
    summary: dict[str, Any],
    comfort: pd.DataFrame,
) -> None:
    metrics = summary["comfort_metrics"]
    baseline = metrics["baseline"]
    controlled = metrics["controlled"]
    streamlit.subheader("Occupied-temperature proxy")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("Baseline compliance", format_comfort(summary["baseline_comfort_percent"])),
            (
                "Controlled compliance",
                format_comfort(summary["controlled_comfort_percent"]),
            ),
            (
                "Comfort change",
                f"{metrics['comfort_change_percent_points']:+.3f} pp",
            ),
            ("Occupied records", f"{controlled['occupied_records']:,}"),
            ("Low violations", f"{controlled['low_temperature_violations']:,}"),
            ("High violations", f"{controlled['high_temperature_violations']:,}"),
            (
                "Average temperature",
                f"{controlled['average_occupied_temperature_c']:.2f} °C",
            ),
            ("Maximum deviation", f"{controlled['maximum_deviation_c']:.2f} °C"),
            (
                "Degree-hours outside",
                f"{controlled['degree_hours_outside_comfort']:.2f}",
            ),
            ("Comfort gate", "Passed" if metrics["comfort_gate_passed"] else "Failed"),
        ):
            streamlit.metric(label, value, border=True)
    streamlit.info(
        "The configured occupied-temperature comfort gate passed, with a "
        "+0.167 percentage-point change relative to baseline."
    )
    streamlit.caption("PMV unavailable in retained EnergyPlus model")
    comfort_chart(
        streamlit,
        comfort,
        source="Phase 10 comfort_comparison.csv",
    )
    comparison_bar_chart(
        streamlit,
        [
            {
                "metric": "Compliance",
                "run": "Fixed-schedule baseline",
                "value": summary["baseline_comfort_percent"],
            },
            {
                "metric": "Compliance",
                "run": "Safety-supervised controlled",
                "value": summary["controlled_comfort_percent"],
            },
            {
                "metric": "Degree-hours outside",
                "run": "Fixed-schedule baseline",
                "value": baseline["degree_hours_outside_comfort"],
            },
            {
                "metric": "Degree-hours outside",
                "run": "Safety-supervised controlled",
                "value": controlled["degree_hours_outside_comfort"],
            },
        ],
        category="metric",
        value="value",
        series="run",
        y_title="Recorded value",
        source="Phase 10 final_summary.json comfort_metrics",
    )


def _control_view(
    streamlit: Any,
    context: dict[str, Any],
    comfort: pd.DataFrame,
    markers: pd.DataFrame,
    show_safety: bool,
    show_fallback: bool,
) -> None:
    streamlit.subheader("Cooling Setpoint Control")
    filtered_line_chart(
        streamlit,
        comfort,
        series={
            "cooling_setpoint_c_baseline": "Fixed-schedule baseline",
            "cooling_setpoint_c_controlled": "Safety-supervised controlled",
        },
        y_title="Cooling setpoint (°C)",
        source="Phase 10 comfort_comparison.csv",
        zero=False,
    )
    streamlit.subheader("Requested, approved, and applied actions")
    action_setpoint_chart(streamlit, markers)
    streamlit.caption(
        "Runtime action years are normalized to the comparison calendar for "
        "display filtering only; original timestamps remain in downloads."
    )
    streamlit.subheader("Requested versus approved values")
    requested_approved_chart(streamlit, markers)
    if show_safety:
        streamlit.subheader("Safety Decisions")
        decision_timeline_chart(
            streamlit,
            markers,
            source="Phase 10 action_summary.csv",
        )
        safety_outcome_chart(streamlit, context["reliability_metrics"])
    if show_fallback:
        runtime = context.get("runtime", {})
        rows = []
        for event_type, key in (
            ("Fallback", "fallbacks"),
            ("Rollback", "rollbacks"),
            ("Emergency", "emergencies"),
        ):
            for item in runtime.get(key, []):
                rows.append(
                    {
                        "timestamp": item.get(
                            "simulation_timestamp",
                            item.get("timestamp"),
                        ),
                        "event_type": event_type,
                        "reason": item.get(
                            "reason_code",
                            item.get("reason", "Not recorded"),
                        ),
                        "fallback_value_c": item.get("fallback_value_c"),
                    }
                )
        streamlit.subheader("Fallback and rollback timeline")
        fallback_timeline_chart(streamlit, pd.DataFrame(rows))


def _impact_view(
    streamlit: Any,
    summary: dict[str, Any],
    cost: pd.DataFrame,
    carbon: pd.DataFrame,
    aggregation: str,
) -> None:
    cost = _aggregate(cost, aggregation)
    carbon = _aggregate(carbon, aggregation)
    if not cost.empty:
        cost["baseline_cumulative_cost"] = cost["baseline_cost"].cumsum()
        cost["controlled_cumulative_cost"] = cost["controlled_cost"].cumsum()
    if not carbon.empty:
        carbon["baseline_cumulative_carbon_kg"] = carbon[
            "baseline_carbon_kg"
        ].cumsum()
    with streamlit.container(horizontal=True, gap="small"):
        streamlit.metric(
            "Cost difference",
            f"−{format_cost(summary['cost_metrics']['absolute_cost_reduction'], summary['cost_metrics']['currency'])}",
            help="Derived from the configured tariff assumption",
            border=True,
        )
        streamlit.metric(
            "Carbon difference",
            f"−{format_carbon(summary['carbon_metrics']['absolute_carbon_reduction_kg'])}",
            help="Derived from the configured carbon-intensity assumption",
            border=True,
        )
        carbon["controlled_cumulative_carbon_kg"] = carbon[
            "controlled_carbon_kg"
        ].cumsum()
    streamlit.subheader("Cost Impact")
    filtered_line_chart(
        streamlit,
        cost,
        series={
            "baseline_cumulative_cost": "Fixed-schedule baseline",
            "controlled_cumulative_cost": "Safety-supervised controlled",
        },
        y_title=f"Cumulative cost ({summary['cost_metrics']['currency']})",
        source="Phase 10 cost_comparison.csv",
        zero=False,
    )
    streamlit.caption(
        "Derived from configured assumption · ₹8/kWh project assumption · "
        f"{summary['cost_metrics']['tariff_source']}"
    )
    streamlit.subheader("Carbon Impact")
    filtered_line_chart(
        streamlit,
        carbon,
        series={
            "baseline_cumulative_carbon_kg": "Fixed-schedule baseline",
            "controlled_cumulative_carbon_kg": "Safety-supervised controlled",
        },
        y_title="Cumulative carbon (kg CO₂)",
        source="Phase 10 carbon_comparison.csv",
        zero=False,
    )
    streamlit.caption(
        "Derived from configured assumption · 708 gCO₂/kWh project assumption · "
        f"{summary['carbon_metrics']['carbon_intensity_source']}"
    )


def _demand_detail(streamlit: Any, summary: dict[str, Any]) -> None:
    demand = summary["demand_metrics"]
    streamlit.subheader("Demand analytics")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("Baseline peak", f"{demand['baseline_peak_demand_kw']:.9f} kW"),
            ("Controlled peak", f"{demand['controlled_peak_demand_kw']:.9f} kW"),
            ("Baseline average", f"{demand['baseline_average_demand_kw']:.3f} kW"),
            ("Controlled average", f"{demand['controlled_average_demand_kw']:.3f} kW"),
            ("Warning threshold", f"{demand['warning_threshold_kw']:.1f} kW"),
            ("Critical threshold", f"{demand['critical_threshold_kw']:.1f} kW"),
            (
                "Warning intervals",
                f"{demand['baseline_intervals_above_warning']:,} / "
                f"{demand['controlled_intervals_above_warning']:,}",
            ),
            (
                "Critical intervals",
                f"{demand['baseline_intervals_above_critical']:,} / "
                f"{demand['controlled_intervals_above_critical']:,}",
            ),
        ):
            streamlit.metric(label, value, border=True)
    streamlit.info("Peak demand essentially unchanged")
    streamlit.caption(
        f"Baseline peak · {demand['baseline_peak_timestamp']} · Controlled peak · "
        f"{demand['controlled_peak_timestamp']}"
    )


def render_analytics(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    product_header(
        streamlit,
        title="Analytics",
        subtitle=(
            "Full-resolution official metrics with filtered, aggregated display "
            "views over the saved Phase 10 EnergyPlus evidence."
        ),
        eyebrow="Measured performance",
        mode=mode,
    )
    try:
        context = load_demo_context()
        summary = context["summary"]
        energy = _timestamp(
            load_comparison_csv("energy_comparison.csv", index=context["index"])
        )
        demand = _timestamp(
            load_comparison_csv("demand_comparison.csv", index=context["index"])
        )
        comfort = _timestamp(
            load_comparison_csv("comfort_comparison.csv", index=context["index"])
        )
        actions = _timestamp(
            load_comparison_csv("action_summary.csv", index=context["index"])
        )
        cost = _timestamp(
            load_comparison_csv("cost_comparison.csv", index=context["index"])
        )
        carbon = _timestamp(
            load_comparison_csv("carbon_comparison.csv", index=context["index"])
        )
        facility = _timestamp(
            load_comparison_csv(
                "aligned_facility_telemetry.csv",
                index=context["index"],
            )
        )
    except ArtifactLoadError as exc:
        safe_page_error(
            streamlit,
            title="Analytics evidence unavailable",
            message=exc.public_message,
            next_step="Rebuild the Phase 10 artifact bundle, then refresh.",
            diagnostics=exc.diagnostics,
        )
        return

    strongest = pd.to_numeric(
        energy["interval_energy_reduction_kwh"],
        errors="coerce",
    ).abs().idxmax()
    center = energy.loc[strongest, "timestamp"]
    minimum = energy["timestamp"].min()
    maximum = energy["timestamp"].max()

    with streamlit.popover("Filters", icon=":material/filter_list:"):
        full_year = streamlit.toggle(
            "Full-year summary",
            value=False,
            key="analytics-full-year",
        )
        if full_year:
            selected_dates = (minimum.date(), maximum.date())
        else:
            selected_dates = streamlit.date_input(
                "Date range",
                value=(
                    max(minimum, center - pd.Timedelta(days=14)).date(),
                    min(maximum, center + pd.Timedelta(days=14)).date(),
                ),
                min_value=minimum.date(),
                max_value=maximum.date(),
                key="analytics-date-range",
            )
        zone = streamlit.selectbox(
            "Zone",
            sorted(comfort["energyplus_zone_name"].dropna().unique()),
            index=sorted(
                comfort["energyplus_zone_name"].dropna().unique()
            ).index(CONTROLLED_ZONE),
            key="analytics-zone",
        )
        metric = streamlit.selectbox(
            "Metric",
            (
                "All metrics",
                "Energy",
                "Demand",
                "Comfort",
                "Control",
                "Cost",
                "Carbon",
            ),
            key="analytics-metric",
        )
        visibility = streamlit.pills(
            "Visible runs",
            ("Baseline", "Controlled"),
            default=("Baseline", "Controlled"),
            selection_mode="multi",
            key="analytics-visibility",
        )
        occupied_only = streamlit.toggle(
            "Occupied only",
            value=True,
            key="analytics-occupied",
        )
        show_actions = streamlit.toggle(
            "Action markers",
            value=True,
            key="analytics-actions",
        )
        show_safety = streamlit.toggle(
            "Safety events",
            value=True,
            key="analytics-safety",
        )
        show_fallback = streamlit.toggle(
            "Fallback events",
            value=True,
            key="analytics-fallback",
        )
        aggregation = streamlit.segmented_control(
            "Aggregation",
            ("Hourly", "Daily", "Monthly"),
            default="Daily",
            key="analytics-aggregation",
        )

    if full_year:
        start, end = minimum, maximum
    else:
        if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
            selected_dates = (minimum.date(), maximum.date())
        start = pd.Timestamp(selected_dates[0])
        end = pd.Timestamp(selected_dates[1]) + pd.Timedelta(days=1) - pd.Timedelta(
            microseconds=1
        )
    energy_filtered = _filter_dates(energy, start, end)
    demand_filtered = _filter_dates(demand, start, end)
    facility_filtered = _filter_dates(facility, start, end)
    comfort_filtered = _filter_dates(comfort, start, end)
    comfort_filtered = comfort_filtered.loc[
        comfort_filtered["energyplus_zone_name"].eq(zone)
    ]
    if occupied_only:
        comfort_filtered = comfort_filtered.loc[
            pd.to_numeric(
                comfort_filtered["occupancy_controlled"],
                errors="coerce",
            ).fillna(0)
            > 0
        ]
    cost_filtered = _filter_dates(cost, start, end)
    carbon_filtered = _filter_dates(carbon, start, end)
    markers = _calendar_action_markers(actions, start, end)
    action_markers = markers if show_actions else pd.DataFrame()

    _render_summary(streamlit, summary)
    streamlit.caption(
        f"Displayed range · {start.date()} to {end.date()} · {zone} · "
        f"{aggregation.lower()} visualization. Official totals above remain "
        "full-resolution and are never recomputed from display data."
    )
    view = streamlit.segmented_control(
        "Analytics view",
        ("Overview", "Energy", "Comfort", "Control", "Impact"),
        default="Overview",
        key="analytics-view",
    )
    if metric != "All metrics":
        view = {
            "Energy": "Energy",
            "Demand": "Energy",
            "Comfort": "Comfort",
            "Control": "Control",
            "Cost": "Impact",
            "Carbon": "Impact",
        }[metric]
        streamlit.caption(f"Metric filter applied · {metric}")
    if view in {"Overview", "Energy"}:
        _energy_view(
            streamlit,
            context,
            energy_filtered,
            demand_filtered,
            facility_filtered,
            action_markers,
            list(visibility or ("Baseline", "Controlled")),
            str(aggregation),
        )
        _demand_detail(streamlit, summary)
    if view in {"Overview", "Comfort"}:
        _comfort_view(streamlit, summary, comfort_filtered)
    if view in {"Overview", "Control"}:
        _control_view(
            streamlit,
            context,
            comfort_filtered,
            markers,
            show_safety,
            show_fallback,
        )
    if view in {"Overview", "Impact"}:
        _impact_view(
            streamlit,
            summary,
            cost_filtered,
            carbon_filtered,
            str(aggregation),
        )

    streamlit.caption(
        "Whole-building effect is small because one zone is controlled under "
        "strict safety limits. Cost and carbon are derived values, not direct "
        "EnergyPlus outputs."
    )


__all__ = ["render_analytics"]
