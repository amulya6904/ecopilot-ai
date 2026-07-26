"""Clear, unit-labelled Phase 10 chart construction and export."""

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _line(
    frame: pd.DataFrame,
    *,
    x: str,
    columns: list[str],
    title: str,
    y_title: str,
    zero_axis: bool = False,
) -> go.Figure:
    figure = go.Figure()
    for column in columns:
        if column not in frame:
            continue
        figure.add_trace(
            go.Scatter(
                x=frame[x],
                y=frame[column],
                mode="lines",
                name=column.replace("_", " ").title(),
            )
        )
    figure.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=y_title,
        template="plotly_white",
        legend_title_text="Series",
    )
    if zero_axis:
        figure.update_yaxes(rangemode="tozero")
    return figure


def build_chart_figures(
    *,
    energy: pd.DataFrame,
    demand: pd.DataFrame,
    comfort: pd.DataFrame,
    cost: pd.DataFrame,
    carbon: pd.DataFrame,
    actions: pd.DataFrame,
    reliability: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, go.Figure]:
    figures: dict[str, go.Figure] = {
        "cumulative_energy": _line(
            energy,
            x="timestamp",
            columns=[
                "baseline_cumulative_energy_kwh",
                "controlled_cumulative_energy_kwh",
            ],
            title="Cumulative facility electricity",
            y_title="Electricity (kWh)",
            zero_axis=True,
        ),
        "interval_electricity": _line(
            energy,
            x="timestamp",
            columns=["baseline_energy_kwh", "controlled_energy_kwh"],
            title="Interval facility electricity",
            y_title="Electricity (kWh)",
            zero_axis=True,
        ),
        "facility_demand": _line(
            demand,
            x="timestamp",
            columns=["baseline_demand_kw", "controlled_demand_kw"],
            title="Facility electricity demand",
            y_title="Demand (kW)",
            zero_axis=True,
        ),
        "cost_comparison": _line(
            cost,
            x="timestamp",
            columns=["baseline_cost", "controlled_cost"],
            title="Interval derived electricity cost",
            y_title="Cost",
            zero_axis=True,
        ),
        "carbon_comparison": _line(
            carbon,
            x="timestamp",
            columns=["baseline_carbon_kg", "controlled_carbon_kg"],
            title="Interval derived carbon emissions",
            y_title="Carbon (kg CO2e)",
            zero_axis=True,
        ),
    }
    if not demand.empty:
        peak = pd.DataFrame({
            "Run": ["Baseline", "Controlled"],
            "Peak demand (kW)": [
                pd.to_numeric(
                    demand["baseline_demand_kw"], errors="coerce"
                ).max(),
                pd.to_numeric(
                    demand["controlled_demand_kw"], errors="coerce"
                ).max(),
            ],
        })
        figure = px.bar(
            peak,
            x="Run",
            y="Peak demand (kW)",
            title="Peak facility demand",
            text_auto=".3f",
        )
        figure.update_yaxes(rangemode="tozero")
        figure.update_layout(template="plotly_white")
        figures["peak_demand"] = figure
    occupied = (
        comfort.loc[
            pd.to_numeric(
                comfort["occupancy_controlled"], errors="coerce"
            ).fillna(0)
            > 0
        ].copy()
        if not comfort.empty and "occupancy_controlled" in comfort
        else pd.DataFrame()
    )
    if not occupied.empty:
        figures["occupied_temperature"] = _line(
            occupied,
            x="timestamp",
            columns=[
                "indoor_temperature_c_baseline",
                "indoor_temperature_c_controlled",
            ],
            title="Occupied temperature",
            y_title="Temperature (°C)",
        )
        figures["comfort_boundaries"] = _line(
            occupied,
            x="timestamp",
            columns=[
                "indoor_temperature_c_controlled",
                "comfort_min_c",
                "comfort_max_c",
            ],
            title="Controlled occupied temperature and comfort boundaries",
            y_title="Temperature (°C)",
        )
        figures["baseline_controlled_setpoints"] = _line(
            occupied,
            x="timestamp",
            columns=[
                "cooling_setpoint_c_baseline",
                "cooling_setpoint_c_controlled",
            ],
            title="Baseline and controlled cooling setpoints",
            y_title="Cooling setpoint (°C)",
        )
    if not actions.empty:
        figures["requested_approved_applied_actions"] = _line(
            actions,
            x="timestamp",
            columns=[
                "requested_setpoint_c",
                "approved_setpoint_c",
                "applied_setpoint_c",
                "observed_setpoint_c",
            ],
            title="Requested, approved, applied, and observed actions",
            y_title="Cooling setpoint (°C)",
        )
        event_frame = actions.loc[
            actions["fallback"].astype(bool)
            | actions["rollback"].astype(bool)
        ].copy()
        event_frame["event"] = event_frame.apply(
            lambda row: (
                "Rollback" if bool(row["rollback"]) else "Fallback"
            ),
            axis=1,
        )
        figures["fallback_rollback_timeline"] = px.scatter(
            event_frame,
            x="timestamp",
            y="event",
            color="event",
            title="Fallback and rollback timeline",
        )
        figures["fallback_rollback_timeline"].update_layout(
            template="plotly_white"
        )
    reliability_frame = pd.DataFrame({
        "Metric": [
            "Completion %",
            "Applied actions",
            "Verified changes",
            "Fallbacks",
            "Rollbacks",
            "LLM timeouts",
            "MCP failures",
        ],
        "Value": [
            reliability.get("completion_percent", 0),
            reliability.get("applied_actions", 0),
            reliability.get("verified_actuator_changes", 0),
            reliability.get("fallbacks", 0),
            reliability.get("rollbacks", 0),
            reliability.get("llm_timeouts", 0),
            reliability.get("mcp_failures", 0),
        ],
    })
    figures["reliability_metrics"] = px.bar(
        reliability_frame,
        x="Metric",
        y="Value",
        title="Reliability metrics",
        text_auto=".3g",
    )
    figures["reliability_metrics"].update_yaxes(rangemode="tozero")
    figures["reliability_metrics"].update_layout(template="plotly_white")
    safety_frame = pd.DataFrame({
        "Outcome": [
            "Unsafe prevented",
            "Comfort-risk prevented",
            "Demand-risk prevented",
            "Stale rejections",
            "Oscillation detections",
            "Actuator mismatches",
        ],
        "Count": [
            safety.get("unsafe_actions_prevented", 0),
            safety.get("comfort_risk_actions_prevented", 0),
            safety.get("demand_risk_actions_prevented", 0),
            safety.get("stale_data_rejections", 0),
            safety.get("oscillation_detections", 0),
            safety.get("actuator_mismatches", 0),
        ],
    })
    figures["safety_outcomes"] = px.bar(
        safety_frame,
        x="Outcome",
        y="Count",
        title="Safety interventions",
        text_auto=True,
    )
    figures["safety_outcomes"].update_yaxes(rangemode="tozero")
    figures["safety_outcomes"].update_layout(template="plotly_white")
    return figures


def write_charts(
    figures: dict[str, go.Figure], charts_directory: Path
) -> dict[str, str]:
    charts_directory.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    for name, figure in figures.items():
        path = charts_directory / f"{name}.html"
        figure.write_html(
            path,
            include_plotlyjs="cdn",
            full_html=True,
        )
        result[name] = str(path.name)
    return result


__all__ = ["build_chart_figures", "write_charts"]
