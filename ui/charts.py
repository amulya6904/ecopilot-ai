"""Unified restrained Altair charts derived from persisted evidence only."""

import math
from typing import Any

import altair as alt
import pandas as pd

from .tokens import CHART_COLORS, TOKENS


def downsample_for_display(
    frame: pd.DataFrame,
    *,
    maximum_rows: int = 2_400,
) -> pd.DataFrame:
    """Sample display rows while retaining the first and exact final values."""
    if len(frame) <= maximum_rows:
        return frame.copy()
    step = max(1, math.ceil(len(frame) / maximum_rows))
    sampled = frame.iloc[::step].copy()
    if sampled.index[-1] != frame.index[-1]:
        sampled = pd.concat([sampled, frame.iloc[[-1]]])
    return sampled


def series_color_scale(labels: list[str]) -> alt.Scale:
    """Create a stable semantic color scale for the supplied display labels."""
    fallback = (
        TOKENS.chart_baseline,
        TOKENS.chart_controlled,
        TOKENS.chart_requested,
        TOKENS.chart_approved,
        TOKENS.chart_fallback,
        TOKENS.chart_emergency,
    )
    colors = [
        CHART_COLORS.get(label, fallback[index % len(fallback)])
        for index, label in enumerate(labels)
    ]
    return alt.Scale(domain=labels, range=colors)


def _finish(chart: alt.TopLevelMixin, *, height: int) -> alt.TopLevelMixin:
    return (
        chart.properties(height=height)
        .configure_view(stroke=None)
        .configure_axis(
            domainColor=TOKENS.border_strong,
            gridColor=TOKENS.border,
            gridOpacity=0.45,
            labelColor=TOKENS.ink_secondary,
            labelFont="Segoe UI",
            labelFontSize=11,
            tickColor=TOKENS.border_strong,
            titleColor=TOKENS.ink_secondary,
            titleFont="Segoe UI",
            titleFontSize=12,
            titleFontWeight=500,
        )
        .configure_legend(
            direction="horizontal",
            labelColor=TOKENS.ink_secondary,
            labelFont="Segoe UI",
            labelFontSize=11,
            orient="bottom",
            symbolStrokeWidth=3,
            title=None,
        )
    )


def comparison_line_chart(
    streamlit: Any,
    frame: pd.DataFrame,
    *,
    series: dict[str, str],
    y_title: str,
    height: int = 330,
    maximum_rows: int = 2_400,
    zero: bool = True,
    show_endpoints: bool = False,
) -> None:
    available = [
        column
        for column in series
        if column in frame and frame[column].notna().any()
    ]
    if not available:
        streamlit.info(f"No measured {y_title.lower()} data is available.")
        return
    sampled = downsample_for_display(
        frame[["timestamp", *available]],
        maximum_rows=maximum_rows,
    )
    sampled["timestamp"] = pd.to_datetime(sampled["timestamp"])
    long = sampled.melt(
        id_vars="timestamp",
        value_vars=available,
        var_name="series",
        value_name="value",
    )
    long["series"] = long["series"].map(series)
    labels = [series[column] for column in available]
    base = alt.Chart(long).encode(
        x=alt.X(
            "timestamp:T",
            title="Simulation date",
            axis=alt.Axis(grid=False, tickCount=7, format="%b"),
        ),
        y=alt.Y("value:Q", title=y_title, scale=alt.Scale(zero=zero)),
        color=alt.Color(
            "series:N",
            title=None,
            scale=series_color_scale(labels),
            sort=labels,
        ),
        tooltip=[
            alt.Tooltip("timestamp:T", title="Timestamp"),
            alt.Tooltip("series:N", title="Series"),
            alt.Tooltip("value:Q", title=y_title, format=",.4f"),
        ],
    )
    layers: alt.TopLevelMixin = base.mark_line(strokeWidth=2)
    if show_endpoints:
        endpoints = (
            long.sort_values("timestamp")
            .groupby("series", as_index=False)
            .tail(1)
        )
        points = (
            alt.Chart(endpoints)
            .mark_point(filled=True, size=70)
            .encode(
                x="timestamp:T",
                y="value:Q",
                color=alt.Color(
                    "series:N",
                    scale=series_color_scale(labels),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("series:N", title="Final series"),
                    alt.Tooltip("value:Q", title="Final value", format=",.6f"),
                ],
            )
        )
        layers = layers + points
    streamlit.altair_chart(_finish(layers, height=height), width="stretch")
    if len(frame) > len(sampled):
        streamlit.caption(
            f"Display sampled to {len(sampled):,} points; calculations and "
            "downloads retain all rows and exact endpoints."
        )


def action_setpoint_chart(
    streamlit: Any,
    actions: pd.DataFrame,
    *,
    height: int = 320,
) -> None:
    if actions.empty:
        streamlit.info("No applied-action rows are available.")
        return
    columns = {
        "requested_setpoint_c": "Requested",
        "approved_setpoint_c": "Approved",
        "applied_setpoint_c": "Applied",
        "observed_setpoint_c": "Observed",
    }
    available = [name for name in columns if name in actions]
    frame = actions[["timestamp", "decision", "fallback", *available]].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    long = frame.melt(
        id_vars=["timestamp", "decision", "fallback"],
        value_vars=available,
        var_name="series",
        value_name="setpoint_c",
    )
    long["series"] = long["series"].map(columns)
    labels = [columns[name] for name in available]
    base = alt.Chart(long).encode(
        x=alt.X(
            "timestamp:T",
            title="Runtime action date",
            axis=alt.Axis(grid=False, tickCount=7, format="%b"),
        ),
        y=alt.Y(
            "setpoint_c:Q",
            title="Cooling setpoint (°C)",
            scale=alt.Scale(zero=False),
        ),
        color=alt.Color(
            "series:N",
            title=None,
            scale=series_color_scale(labels),
            sort=labels,
        ),
        tooltip=[
            alt.Tooltip("timestamp:T", title="Timestamp"),
            alt.Tooltip("series:N", title="Setpoint"),
            alt.Tooltip("setpoint_c:Q", title="Value (°C)", format=".2f"),
            alt.Tooltip("decision:N", title="Safety decision"),
        ],
    )
    lines = base.mark_line(point=alt.OverlayMarkDef(size=28), strokeWidth=1.7)
    fallback_rows = long.loc[long["fallback"].fillna(False)]
    layers: alt.TopLevelMixin = lines
    if not fallback_rows.empty:
        fallback = (
            alt.Chart(fallback_rows)
            .mark_point(
                shape="triangle",
                size=105,
                color=TOKENS.chart_fallback,
            )
            .encode(
                x="timestamp:T",
                y="setpoint_c:Q",
                tooltip=["timestamp:T", "decision:N"],
            )
        )
        layers = layers + fallback
    streamlit.altair_chart(_finish(layers, height=height), width="stretch")


def requested_approved_chart(
    streamlit: Any,
    actions: pd.DataFrame,
    *,
    height: int = 300,
) -> None:
    """Show proposal-to-approval agreement against an honest 1:1 line."""
    required = {"requested_setpoint_c", "approved_setpoint_c", "decision"}
    if actions.empty or not required.issubset(actions.columns):
        streamlit.info("Requested-versus-approved evidence is unavailable.")
        return
    frame = actions[list(required)].dropna().copy()
    minimum = min(
        frame["requested_setpoint_c"].min(),
        frame["approved_setpoint_c"].min(),
    )
    maximum = max(
        frame["requested_setpoint_c"].max(),
        frame["approved_setpoint_c"].max(),
    )
    diagonal = pd.DataFrame({"value": [minimum, maximum]})
    points = (
        alt.Chart(frame)
        .mark_circle(
            size=55,
            color=TOKENS.chart_approved,
            opacity=0.72,
        )
        .encode(
            x=alt.X(
                "requested_setpoint_c:Q",
                title="Requested setpoint (°C)",
                scale=alt.Scale(zero=False),
            ),
            y=alt.Y(
                "approved_setpoint_c:Q",
                title="Approved setpoint (°C)",
                scale=alt.Scale(zero=False),
            ),
            tooltip=[
                alt.Tooltip(
                    "requested_setpoint_c:Q",
                    title="Requested (°C)",
                    format=".2f",
                ),
                alt.Tooltip(
                    "approved_setpoint_c:Q",
                    title="Approved (°C)",
                    format=".2f",
                ),
                alt.Tooltip("decision:N", title="Decision"),
            ],
        )
    )
    one_to_one = (
        alt.Chart(diagonal)
        .mark_line(
            color=TOKENS.chart_requested,
            strokeDash=[5, 4],
        )
        .encode(x="value:Q", y="value:Q")
    )
    streamlit.altair_chart(
        _finish(points + one_to_one, height=height),
        width="stretch",
    )


def safety_outcome_chart(
    streamlit: Any,
    reliability: dict[str, object],
    *,
    height: int = 260,
) -> None:
    """Render deterministic proposal outcomes from persisted reliability data."""
    frame = pd.DataFrame(
        [
            ("Approved", int(reliability["approvals"]), TOKENS.chart_approved),
            ("Clamped", int(reliability["clamps"]), TOKENS.chart_controlled),
            ("Held", int(reliability["holds"]), TOKENS.chart_requested),
            ("Rejected", int(reliability["rejections"]), TOKENS.chart_emergency),
            ("Fallback", int(reliability["fallbacks"]), TOKENS.chart_fallback),
            (
                "Emergency fallback",
                int(reliability["emergency_fallbacks"]),
                TOKENS.chart_emergency,
            ),
        ],
        columns=("outcome", "count", "color"),
    )
    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=1)
        .encode(
            x=alt.X("count:Q", title="Recorded outcomes", scale=alt.Scale(zero=True)),
            y=alt.Y("outcome:N", title=None, sort=None),
            color=alt.Color(
                "outcome:N",
                legend=None,
                scale=alt.Scale(
                    domain=frame["outcome"].tolist(),
                    range=frame["color"].tolist(),
                ),
            ),
            tooltip=[
                alt.Tooltip("outcome:N", title="Outcome"),
                alt.Tooltip("count:Q", title="Count", format=","),
            ],
        )
    )
    streamlit.altair_chart(_finish(chart, height=height), width="stretch")


def fallback_timeline_chart(
    streamlit: Any,
    events: pd.DataFrame,
    *,
    height: int = 190,
) -> None:
    if events.empty:
        streamlit.info("No fallback, rollback, or emergency events were recorded.")
        return
    frame = events.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    domain = ["Fallback", "Rollback", "Emergency"]
    colors = [
        TOKENS.chart_fallback,
        TOKENS.chart_emergency,
        TOKENS.chart_emergency,
    ]
    chart = (
        alt.Chart(frame)
        .mark_tick(thickness=1.5, size=22)
        .encode(
            x=alt.X(
                "timestamp:T",
                title="Simulation date",
                axis=alt.Axis(grid=False, tickCount=7, format="%b"),
            ),
            y=alt.Y("event_type:N", title=None, sort=domain),
            color=alt.Color(
                "event_type:N",
                title=None,
                scale=alt.Scale(domain=domain, range=colors),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip("event_type:N", title="Event"),
                alt.Tooltip("reason:N", title="Reason"),
                alt.Tooltip(
                    "fallback_value_c:Q",
                    title="Fallback value (°C)",
                    format=".2f",
                ),
            ],
        )
    )
    streamlit.altair_chart(_finish(chart, height=height), width="stretch")


__all__ = [
    "action_setpoint_chart",
    "comparison_line_chart",
    "downsample_for_display",
    "fallback_timeline_chart",
    "requested_approved_chart",
    "safety_outcome_chart",
    "series_color_scale",
]
