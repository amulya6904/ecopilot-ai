"""Phase 12 Altair charts over full-resolution persisted comparison data."""

from typing import Any

import altair as alt
import pandas as pd

from ui.charts import downsample_for_display, series_color_scale
from ui.tokens import TOKENS


def _base_config(chart: alt.TopLevelMixin, height: int = 340) -> alt.TopLevelMixin:
    return (
        chart.properties(height=height)
        .configure_view(stroke=None)
        .configure_axis(
            domainColor=TOKENS.border_strong,
            gridColor=TOKENS.border,
            gridOpacity=0.35,
            labelColor=TOKENS.ink_secondary,
            labelFont="Segoe UI",
            labelFontSize=12,
            tickColor=TOKENS.border_strong,
            titleColor=TOKENS.ink_secondary,
            titleFont="Segoe UI",
            titleFontSize=13,
            titlePadding=10,
        )
        .configure_legend(
            orient="bottom",
            direction="horizontal",
            title=None,
            labelColor=TOKENS.ink_secondary,
            labelFontSize=12,
            labelLimit=260,
            symbolSize=110,
        )
    )


def filtered_line_chart(
    streamlit: Any,
    frame: pd.DataFrame,
    *,
    series: dict[str, str],
    y_title: str,
    source: str,
    zero: bool = True,
    action_markers: pd.DataFrame | None = None,
) -> None:
    available = [
        column
        for column in series
        if column in frame.columns and frame[column].notna().any()
    ]
    if frame.empty or not available:
        streamlit.info(f"No {y_title.lower()} evidence is available for this filter.")
        return
    display = downsample_for_display(
        frame[["timestamp", *available]].dropna(subset=["timestamp"]),
        maximum_rows=2_400,
    )
    display["timestamp"] = pd.to_datetime(display["timestamp"], errors="coerce")
    long = display.melt(
        id_vars="timestamp",
        value_vars=available,
        var_name="series",
        value_name="value",
    )
    long["series"] = long["series"].map(series)
    labels = [series[column] for column in available]
    base = (
        alt.Chart(long)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X(
                "timestamp:T",
                title="Simulation time",
                axis=alt.Axis(grid=False, tickCount=6),
            ),
            y=alt.Y(
                "value:Q",
                title=y_title,
                scale=alt.Scale(zero=zero),
            ),
            color=alt.Color(
                "series:N",
                scale=series_color_scale(labels),
                sort=labels,
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title=y_title, format=",.4f"),
            ],
        )
    )
    layered: alt.TopLevelMixin = base
    if action_markers is not None and not action_markers.empty:
        marker_frame = action_markers.copy()
        marker_frame["timestamp"] = pd.to_datetime(
            marker_frame["timestamp"],
            errors="coerce",
        )
        rules = (
            alt.Chart(marker_frame)
            .mark_rule(
                color=TOKENS.chart_approved,
                opacity=0.35,
                strokeDash=[4, 3],
            )
            .encode(
                x="timestamp:T",
                tooltip=[
                    alt.Tooltip("timestamp:T", title="Action"),
                    alt.Tooltip("decision:N", title="Decision"),
                ],
            )
        )
        layered = base + rules
    streamlit.altair_chart(_base_config(layered), width="stretch")
    streamlit.caption(
        f"Source · {source}. Display rendering may be sampled; official totals "
        "and downloaded files remain full resolution."
    )


def comfort_chart(
    streamlit: Any,
    frame: pd.DataFrame,
    *,
    source: str,
) -> None:
    if frame.empty:
        streamlit.info("No occupied-zone temperature evidence matches the filters.")
        return
    display = downsample_for_display(frame, maximum_rows=2_400).copy()
    display["timestamp"] = pd.to_datetime(display["timestamp"], errors="coerce")
    temperature = display.melt(
        id_vars="timestamp",
        value_vars=[
            column
            for column in (
                "indoor_temperature_c_baseline",
                "indoor_temperature_c_controlled",
            )
            if column in display
        ],
        var_name="series",
        value_name="temperature_c",
    )
    temperature["series"] = temperature["series"].map(
        {
            "indoor_temperature_c_baseline": "Fixed-schedule baseline",
            "indoor_temperature_c_controlled": "Safety-supervised controlled",
        }
    )
    bounds = (
        alt.Chart(display)
        .mark_area(color=TOKENS.verified_bg, opacity=0.65)
        .encode(
            x=alt.X("timestamp:T", title="Simulation time", axis=alt.Axis(grid=False)),
            y=alt.Y(
                "comfort_min_c:Q",
                title="Occupied-zone temperature (°C)",
                scale=alt.Scale(zero=False),
            ),
            y2="comfort_max_c:Q",
        )
    )
    lines = (
        alt.Chart(temperature)
        .mark_line(strokeWidth=1.8)
        .encode(
            x="timestamp:T",
            y=alt.Y("temperature_c:Q", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                scale=series_color_scale(
                    ["Fixed-schedule baseline", "Safety-supervised controlled"]
                ),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip(
                    "temperature_c:Q",
                    title="Temperature (°C)",
                    format=".2f",
                ),
            ],
        )
    )
    streamlit.altair_chart(_base_config(bounds + lines), width="stretch")
    streamlit.caption(
        f"Source · {source}. Shaded band is the configured 22–25 °C "
        "occupied-temperature proxy range; PMV is unavailable."
    )


def comparison_bar_chart(
    streamlit: Any,
    rows: list[dict[str, Any]],
    *,
    category: str,
    value: str,
    series: str,
    y_title: str,
    source: str,
) -> None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        streamlit.info(f"No {y_title.lower()} data is available.")
        return
    labels = list(dict.fromkeys(frame[series].astype(str)))
    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(f"{category}:N", title=None),
            xOffset=alt.XOffset(f"{series}:N"),
            y=alt.Y(f"{value}:Q", title=y_title, scale=alt.Scale(zero=True)),
            color=alt.Color(
                f"{series}:N",
                scale=series_color_scale(labels),
            ),
            tooltip=[
                alt.Tooltip(f"{category}:N", title="Metric"),
                alt.Tooltip(f"{series}:N", title="Run"),
                alt.Tooltip(f"{value}:Q", title=y_title, format=",.4f"),
            ],
        )
    )
    streamlit.altair_chart(_base_config(chart, height=300), width="stretch")
    streamlit.caption(f"Source · {source}.")


def decision_timeline_chart(
    streamlit: Any,
    frame: pd.DataFrame,
    *,
    source: str,
) -> None:
    if frame.empty:
        streamlit.info("No decision events match the selected filters.")
        return
    display = frame.copy()
    display["timestamp"] = pd.to_datetime(display["timestamp"], errors="coerce")
    domain = [
        "approve",
        "approve_with_clamp",
        "hold",
        "reject",
        "fallback",
        "rollback",
        "emergency_fallback",
    ]
    colors = [
        TOKENS.chart_approved,
        TOKENS.chart_controlled,
        TOKENS.chart_requested,
        TOKENS.chart_emergency,
        TOKENS.chart_fallback,
        TOKENS.chart_emergency,
        TOKENS.chart_emergency,
    ]
    chart = (
        alt.Chart(display)
        .mark_circle(size=70, opacity=0.8)
        .encode(
            x=alt.X("timestamp:T", title="Decision time", axis=alt.Axis(grid=False)),
            y=alt.Y("decision:N", title="Safety outcome", sort=domain),
            color=alt.Color(
                "decision:N",
                scale=alt.Scale(domain=domain, range=colors),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip("decision:N", title="Outcome"),
                alt.Tooltip("requested_setpoint_c:Q", title="Requested (°C)"),
                alt.Tooltip("approved_setpoint_c:Q", title="Approved (°C)"),
            ],
        )
    )
    streamlit.altair_chart(_base_config(chart, height=270), width="stretch")
    streamlit.caption(f"Source · {source}.")


__all__ = [
    "comfort_chart",
    "comparison_bar_chart",
    "decision_timeline_chart",
    "filtered_line_chart",
]
