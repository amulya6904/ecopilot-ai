"""Readable Altair charts derived only from persisted comparison artifacts."""

import math
from typing import Any

import altair as alt
import pandas as pd


def downsample_for_display(
    frame: pd.DataFrame,
    *,
    maximum_rows: int = 2_400,
) -> pd.DataFrame:
    if len(frame) <= maximum_rows:
        return frame.copy()
    step = max(1, math.ceil(len(frame) / maximum_rows))
    sampled = frame.iloc[::step].copy()
    if sampled.index[-1] != frame.index[-1]:
        sampled = pd.concat([sampled, frame.iloc[[-1]]])
    return sampled


def comparison_line_chart(
    streamlit: Any,
    frame: pd.DataFrame,
    *,
    series: dict[str, str],
    y_title: str,
    height: int = 330,
    maximum_rows: int = 2_400,
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
    chart = (
        alt.Chart(long)
        .mark_line()
        .encode(
            x=alt.X("timestamp:T", title="Simulation timestamp"),
            y=alt.Y("value:Q", title=y_title, scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", title=None),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title=y_title, format=",.4f"),
            ],
        )
        .properties(height=height)
        .interactive(bind_y=False)
    )
    streamlit.altair_chart(chart, width="stretch")
    if len(frame) > len(sampled):
        streamlit.caption(
            f"Display sampled to {len(sampled):,} points; calculations and "
            "downloads retain all rows."
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
    lines = (
        alt.Chart(long)
        .mark_line(point=True)
        .encode(
            x=alt.X("timestamp:T", title="Runtime action timestamp"),
            y=alt.Y(
                "setpoint_c:Q",
                title="Cooling setpoint (°C)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color("series:N", title=None),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip("series:N", title="Setpoint"),
                alt.Tooltip("setpoint_c:Q", title="Value (°C)", format=".2f"),
                alt.Tooltip("decision:N", title="Safety decision"),
            ],
        )
    )
    fallback = (
        alt.Chart(long.loc[long["fallback"].fillna(False)])
        .mark_point(shape="triangle", size=110, color="#B42318")
        .encode(
            x="timestamp:T",
            y="setpoint_c:Q",
            tooltip=["timestamp:T", "decision:N"],
        )
    )
    streamlit.altair_chart(
        (lines + fallback).properties(height=height),
        width="stretch",
    )


__all__ = [
    "action_setpoint_chart",
    "comparison_line_chart",
    "downsample_for_display",
]
