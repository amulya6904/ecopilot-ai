"""Artifact-backed Phase 10 comparison and final validation dashboard."""

from io import BytesIO
from pathlib import Path
import zipfile

import pandas as pd
import streamlit as st

from comparison.artifacts import REQUIRED_COMPARISON_ARTIFACTS
from .artifact_views import (
    PROJECT_ROOT,
    latest_phase10_directory,
    load_phase10_bundle,
)
from .charts import action_setpoint_chart, comparison_line_chart
from .constants import (
    COMFORT_WORDING,
    HONEST_RESULT_CLAIM,
    SMALL_RESULT_NOTE,
)
from .formatting import (
    format_carbon,
    format_comfort,
    format_cost,
    format_demand,
    format_energy,
    format_percent,
    peak_change_label,
    project_relative,
)


def _latest_directory() -> Path | None:
    """Return the newest valid comparison, including a pending repeat."""
    return latest_phase10_directory(require_reproducible=False)


def phase10_complete() -> bool:
    """Report completion only for a valid, reproducible artifact bundle."""
    directory = latest_phase10_directory(require_reproducible=True)
    if directory is None:
        return False
    try:
        bundle = load_phase10_bundle(str(directory.resolve()))
    except (OSError, ValueError, KeyError):
        return False
    summary = bundle["summary"]
    return bool(
        summary.get("comparison_valid")
        and summary.get("reproducible")
        and all(
            (directory / filename).is_file()
            for filename in REQUIRED_COMPARISON_ARTIFACTS
        )
    )


def _load_bundle(directory_text: str) -> dict[str, object]:
    """Compatibility wrapper retained for existing tests and imports."""
    return load_phase10_bundle(directory_text)


@st.cache_data(ttl=60, max_entries=4, show_spinner=False)
def _chart_archive(directory_text: str) -> bytes:
    directory = Path(directory_text) / "charts"
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for chart in sorted(directory.glob("*.html")):
            archive.write(chart, chart.name)
    return stream.getvalue()


def _format(value: object, suffix: str, decimals: int = 3) -> str:
    """Compatibility formatter retained for Phase 10 unit tests."""
    if value is None:
        return "Unavailable"
    return f"{float(value):,.{decimals}f}{suffix}"


def _calendar_key(values: pd.Series) -> pd.Series:
    timestamps = pd.to_datetime(values, errors="coerce", utc=True)
    return timestamps.dt.strftime("%m-%d %H:%M")


def build_action_impact_table(
    actions: pd.DataFrame,
    energy: pd.DataFrame,
    comfort: pd.DataFrame,
) -> pd.DataFrame:
    """Join action evidence to aligned interval data by calendar timestamp."""
    if actions.empty:
        return pd.DataFrame()
    action_frame = actions.copy()
    action_frame["_calendar_key"] = _calendar_key(action_frame["timestamp"])

    energy_columns = [
        "timestamp",
        "baseline_energy_kwh",
        "controlled_energy_kwh",
        "interval_energy_reduction_kwh",
    ]
    energy_frame = energy[energy_columns].copy()
    energy_frame["_calendar_key"] = _calendar_key(energy_frame["timestamp"])
    energy_frame = energy_frame.drop(columns="timestamp")

    zone_frame = comfort.loc[
        comfort["energyplus_zone_name"].eq("SPACE1-1"),
        [
            "timestamp",
            "energyplus_zone_name",
            "cooling_setpoint_c_baseline",
        ],
    ].copy()
    zone_frame["_calendar_key"] = _calendar_key(zone_frame["timestamp"])
    zone_frame = zone_frame.drop(columns="timestamp")

    merged = action_frame.merge(
        energy_frame,
        on="_calendar_key",
        how="left",
        validate="many_to_one",
    ).merge(
        zone_frame,
        on="_calendar_key",
        how="left",
        validate="many_to_one",
    )
    merged["energyplus_zone_name"] = merged[
        "energyplus_zone_name"
    ].fillna("SPACE1-1")
    selected = merged[
        [
            "timestamp",
            "energyplus_zone_name",
            "cooling_setpoint_c_baseline",
            "requested_setpoint_c",
            "approved_setpoint_c",
            "applied_setpoint_c",
            "observed_setpoint_c",
            "baseline_energy_kwh",
            "controlled_energy_kwh",
            "interval_energy_reduction_kwh",
            "decision",
            "fallback",
            "rollback",
        ]
    ].copy()
    return selected.rename(
        columns={
            "energyplus_zone_name": "zone",
            "cooling_setpoint_c_baseline": "baseline_setpoint_c",
            "baseline_energy_kwh": "baseline_interval_energy_kwh",
            "controlled_energy_kwh": "controlled_interval_energy_kwh",
            "interval_energy_reduction_kwh": "interval_energy_difference_kwh",
            "decision": "safety_decision",
        }
    )


def _metric_row(streamlit, metrics: list[tuple[str, str, str | None]]) -> None:
    columns = streamlit.columns(len(metrics), border=True)
    for column, (label, value, help_text) in zip(columns, metrics, strict=True):
        column.metric(label, value, help=help_text)


def _render_claim(streamlit, summary: dict[str, object], directory: Path) -> None:
    with streamlit.container(border=True):
        streamlit.subheader("Validated result")
        if summary.get("eligible_to_claim_savings"):
            streamlit.success(HONEST_RESULT_CLAIM, icon=":material/verified:")
        else:
            streamlit.warning(
                str(summary.get("exact_approved_statement", "Savings are not claimable.")),
                icon=":material/warning:",
            )
        streamlit.info(SMALL_RESULT_NOTE, icon=":material/info:")
        streamlit.caption(
            "Source: "
            f"{project_relative(directory / 'final_summary.json', PROJECT_ROOT)} "
            f"· Comparison ID: {summary.get('comparison_id', 'Unavailable')}"
        )


def _render_kpis(streamlit, summary: dict[str, object]) -> None:
    demand = summary["demand_metrics"]
    comfort = summary["comfort_metrics"]
    baseline_comfort = comfort["baseline"]
    controlled_comfort = comfort["controlled"]
    cost = summary["cost_metrics"]
    carbon = summary["carbon_metrics"]
    reproducibility = bool(summary.get("reproducible"))

    streamlit.subheader("Headline evidence")
    _metric_row(
        streamlit,
        [
            ("Baseline facility energy", format_energy(summary["baseline_energy_kwh"]), None),
            ("Controlled facility energy", format_energy(summary["controlled_energy_kwh"]), None),
            ("Absolute energy reduction", format_energy(summary["energy_reduction_kwh"], compact=True), None),
            ("Percentage energy reduction", format_percent(summary["energy_reduction_percent"], 4), None),
        ],
    )
    _metric_row(
        streamlit,
        [
            ("Baseline peak", format_demand(summary["baseline_peak_demand_kw"]), None),
            ("Controlled peak", format_demand(summary["controlled_peak_demand_kw"]), None),
            (
                "Peak-demand change",
                peak_change_label(
                    demand["absolute_peak_reduction_kw"],
                    tolerance_kw=1e-6,
                ),
                "The measured absolute change is within the reproducibility tolerance.",
            ),
            (
                "Aligned intervals",
                f"{summary['alignment']['matched_intervals']:,} / "
                f"{summary['alignment']['total_expected_intervals']:,}",
                None,
            ),
        ],
    )
    streamlit.caption(
        "Measured peak-reduction percentage: "
        f"{float(summary['peak_reduction_percent']):.8f}%. "
        "This is reported as essentially unchanged because the absolute "
        "difference is below 0.000001 kW."
    )
    _metric_row(
        streamlit,
        [
            ("Baseline comfort proxy", format_comfort(summary["baseline_comfort_percent"]), None),
            ("Controlled comfort proxy", format_comfort(summary["controlled_comfort_percent"]), None),
            (
                "Comfort change",
                f"{float(comfort['comfort_change_percent_points']):+.3f} pp",
                None,
            ),
            (
                "Comfort gate",
                "Passed" if summary["comfort_gate_passed"] else "Failed",
                None,
            ),
        ],
    )
    streamlit.success(COMFORT_WORDING, icon=":material/check_circle:")
    streamlit.dataframe(
        [
            {
                "Run": "Fixed-schedule baseline",
                "Low-temperature violations": baseline_comfort[
                    "low_temperature_violations"
                ],
                "High-temperature violations": baseline_comfort[
                    "high_temperature_violations"
                ],
                "PMV available": baseline_comfort["pmv_available"],
                "Comfort method": baseline_comfort["comfort_method"],
            },
            {
                "Run": "Safety-supervised controlled",
                "Low-temperature violations": controlled_comfort[
                    "low_temperature_violations"
                ],
                "High-temperature violations": controlled_comfort[
                    "high_temperature_violations"
                ],
                "PMV available": controlled_comfort["pmv_available"],
                "Comfort method": controlled_comfort["comfort_method"],
            },
        ],
        hide_index=True,
        width="stretch",
    )
    _metric_row(
        streamlit,
        [
            (
                "Derived cost change",
                format_cost(cost["absolute_cost_reduction"], cost["currency"]),
                f"Assumption: {cost['flat_tariff_per_kwh']} "
                f"{cost['currency']}/kWh.",
            ),
            (
                "Derived carbon change",
                format_carbon(carbon["absolute_carbon_reduction_kg"]),
                "Assumption: "
                f"{carbon['constant_carbon_intensity_g_per_kwh']} g CO₂/kWh.",
            ),
            (
                "Severe / fatal errors",
                f"{summary['severe_count']} / {summary['fatal_count']}",
                None,
            ),
            (
                "Reproducibility",
                "Verified" if reproducibility else "Not verified",
                None,
            ),
        ],
    )
    streamlit.caption(
        "Cost and carbon are derived from measured electricity using explicit "
        "project assumptions; they are not EnergyPlus-native tariff or grid outputs."
    )


def _render_charts(streamlit, bundle: dict[str, object]) -> None:
    energy = bundle["energy"]
    demand = bundle["demand"]
    comfort = bundle["comfort"]
    actions = bundle["actions"]
    cost = bundle["cost"]
    carbon = bundle["carbon"]

    streamlit.subheader("Measured comparison charts")
    with streamlit.container(border=True):
        streamlit.markdown("**Cumulative facility electricity**")
        comparison_line_chart(
            streamlit,
            energy,
            series={
                "baseline_cumulative_energy_kwh": "Fixed-schedule baseline",
                "controlled_cumulative_energy_kwh": "Safety-supervised controlled",
            },
            y_title="Cumulative facility electricity (kWh)",
        )
    with streamlit.container(border=True):
        streamlit.markdown("**Facility demand**")
        comparison_line_chart(
            streamlit,
            demand,
            series={
                "baseline_demand_kw": "Fixed-schedule baseline",
                "controlled_demand_kw": "Safety-supervised controlled",
            },
            y_title="Facility demand (kW)",
        )
    occupied_zone = comfort.loc[
        comfort["energyplus_zone_name"].eq("SPACE1-1")
        & (
            pd.to_numeric(
                comfort["occupancy_controlled"],
                errors="coerce",
            ).fillna(0)
            > 0
        )
    ]
    with streamlit.container(border=True):
        streamlit.markdown("**Controlled-zone occupied temperature**")
        comparison_line_chart(
            streamlit,
            occupied_zone,
            series={
                "indoor_temperature_c_baseline": "Fixed-schedule baseline",
                "indoor_temperature_c_controlled": "Safety-supervised controlled",
                "comfort_min_c": "Configured lower bound",
                "comfort_max_c": "Configured upper bound",
            },
            y_title="Zone temperature (°C)",
        )
        streamlit.caption(
            "SPACE1-1 only. This is the configured occupied-temperature proxy; "
            "genuine PMV/PPD is unavailable in the retained People objects."
        )
    with streamlit.container(border=True):
        streamlit.markdown("**Requested through observed control actions**")
        action_setpoint_chart(streamlit, actions)
    left, right = streamlit.columns(2)
    with left.container(border=True):
        streamlit.markdown("**Derived interval cost**")
        comparison_line_chart(
            streamlit,
            cost,
            series={
                "baseline_cost": "Fixed-schedule baseline",
                "controlled_cost": "Safety-supervised controlled",
            },
            y_title="Derived interval cost (INR)",
            height=280,
        )
    with right.container(border=True):
        streamlit.markdown("**Derived interval carbon**")
        comparison_line_chart(
            streamlit,
            carbon,
            series={
                "baseline_carbon_kg": "Fixed-schedule baseline",
                "controlled_carbon_kg": "Safety-supervised controlled",
            },
            y_title="Derived interval carbon (kg CO₂)",
            height=280,
        )


def _render_meter_mapping(streamlit) -> None:
    streamlit.subheader("EnergyPlus meter mapping")
    streamlit.dataframe(
        [
            {
                "Displayed quantity": "Facility electricity meter",
                "EnergyPlus source meter / variable": "Electricity:Facility",
                "Unit": "J per hourly interval",
                "Availability": "Available",
                "Display conversion": "J ÷ 3,600,000 → kWh",
            },
            {
                "Displayed quantity": "HVAC electricity meter",
                "EnergyPlus source meter / variable": "Electricity:HVAC",
                "Unit": "J per hourly interval",
                "Availability": "Available",
                "Display conversion": "J ÷ 3,600,000 → kWh",
            },
            {
                "Displayed quantity": "Cooling electricity meter",
                "EnergyPlus source meter / variable": "Cooling:Electricity",
                "Unit": "J per hourly interval",
                "Availability": "Available",
                "Display conversion": "J ÷ 3,600,000 → kWh",
            },
            {
                "Displayed quantity": "Heating electricity meter",
                "EnergyPlus source meter / variable": "Heating:Electricity",
                "Unit": "J per hourly interval",
                "Availability": "Available",
                "Display conversion": "J ÷ 3,600,000 → kWh",
            },
            {
                "Displayed quantity": "Fan electricity meter",
                "EnergyPlus source meter / variable": "Fans:Electricity",
                "Unit": "J per hourly interval",
                "Availability": "Available",
                "Display conversion": "J ÷ 3,600,000 → kWh",
            },
        ],
        hide_index=True,
        width="stretch",
    )
    streamlit.caption(
        "In this retained model, Electricity:HVAC equals Fans:Electricity. "
        "The dashboard presents each requested meter independently and never sums them."
    )


def _render_action_impact(streamlit, bundle: dict[str, object]) -> None:
    streamlit.subheader("Action-to-impact trace")
    table = build_action_impact_table(
        bundle["actions"],
        bundle["energy"],
        bundle["comfort"],
    )
    if table.empty:
        streamlit.info("No applied control actions are present in this comparison.")
        return
    streamlit.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "timestamp": "Runtime action timestamp",
            "zone": "Zone",
            "baseline_setpoint_c": streamlit.column_config.NumberColumn(
                "Baseline setpoint (°C)", format="%.2f"
            ),
            "requested_setpoint_c": streamlit.column_config.NumberColumn(
                "Requested (°C)", format="%.2f"
            ),
            "approved_setpoint_c": streamlit.column_config.NumberColumn(
                "Approved (°C)", format="%.2f"
            ),
            "applied_setpoint_c": streamlit.column_config.NumberColumn(
                "Applied (°C)", format="%.2f"
            ),
            "observed_setpoint_c": streamlit.column_config.NumberColumn(
                "Observed (°C)", format="%.2f"
            ),
            "baseline_interval_energy_kwh": streamlit.column_config.NumberColumn(
                "Baseline interval (kWh)", format="%.5f"
            ),
            "controlled_interval_energy_kwh": streamlit.column_config.NumberColumn(
                "Controlled interval (kWh)", format="%.5f"
            ),
            "interval_energy_difference_kwh": streamlit.column_config.NumberColumn(
                "Baseline − controlled (kWh)", format="%.5f"
            ),
            "safety_decision": "Safety decision",
        },
    )
    streamlit.caption(
        "Runtime actions use the original EnergyPlus calendar year (2013), while "
        "aligned comparison telemetry uses reference year 2000. Rows are joined "
        "only by month, day, and interval-end time; all stored timestamps remain unchanged."
    )


def _render_reliability(streamlit, bundle: dict[str, object]) -> None:
    reliability = bundle["reliability"]
    safety = bundle["safety"]
    summary = bundle["summary"]
    streamlit.subheader("Reliability and deterministic safety")
    _metric_row(
        streamlit,
        [
            ("Run completion", format_percent(reliability["completion_percent"], 1), None),
            ("Applied actions", f"{reliability['applied_actions']:,}", None),
            ("Verified actuator changes", f"{reliability['verified_actuator_changes']:,}", None),
            ("Fallbacks / rollbacks", f"{reliability['fallbacks']:,} / {reliability['rollbacks']:,}", None),
        ],
    )
    streamlit.dataframe(
        [
            {
                "Safety measure": "Unsafe actions prevented",
                "Measured value": str(safety["unsafe_actions_prevented"]),
            },
            {
                "Safety measure": "Comfort-risk actions prevented",
                "Measured value": str(safety["comfort_risk_actions_prevented"]),
            },
            {
                "Safety measure": "Oscillation detections",
                "Measured value": str(safety["oscillation_detections"]),
            },
            {
                "Safety measure": "Actuator mismatches",
                "Measured value": str(safety["actuator_mismatches"]),
            },
            {
                "Safety measure": "Safety intervention rate",
                "Measured value": f"{float(safety['intervention_rate']) * 100:.2f}%",
            },
        ],
        hide_index=True,
        width="stretch",
    )
    streamlit.caption(
        "This final reproducibility policy made no live LLM requests. The local "
        "LLM is advisory in Phase 7; the deterministic Phase 9 supervisor always "
        "retains final actuator authority. "
        f"Control injection verified: {summary['control_injection_verified']}."
    )


def _render_reproducibility(
    streamlit,
    bundle: dict[str, object],
    directory: Path,
) -> None:
    summary = bundle["summary"]
    report = bundle["reproducibility"]
    baseline = bundle["baseline"]
    controlled = bundle["controlled"]
    exact_link = report.get("second_comparison_id") == summary.get("comparison_id")
    streamlit.subheader("Reproducibility chain")
    if report.get("reproducible") and exact_link:
        streamlit.success(
            "The displayed summary is the verified second comparison in the "
            "repeatability check.",
            icon=":material/replay:",
        )
    else:
        streamlit.error(
            "The displayed comparison is not linked to a passing repeatability report."
        )
    streamlit.dataframe(
        [
            {"Evidence": "Displayed comparison", "Value": summary["comparison_id"]},
            {"Evidence": "First comparison", "Value": report["first_comparison_id"]},
            {"Evidence": "Verified repeat", "Value": report["second_comparison_id"]},
            {"Evidence": "Tolerance", "Value": str(report["tolerance"])},
            {"Evidence": "Model hashes match", "Value": str(report["model_hashes_match"])},
            {"Evidence": "Weather hashes match", "Value": str(report["weather_hashes_match"])},
            {"Evidence": "Telemetry shape match", "Value": str(report["telemetry_shape_match"])},
            {"Evidence": "Energy within tolerance", "Value": str(report["energy_within_tolerance"])},
            {"Evidence": "Peak demand within tolerance", "Value": str(report["peak_demand_within_tolerance"])},
            {"Evidence": "Comfort within tolerance", "Value": str(report["comfort_within_tolerance"])},
        ],
        hide_index=True,
        width="stretch",
    )
    with streamlit.expander("Frozen model and weather hashes"):
        streamlit.dataframe(
            [
                {
                    "Hash": "Base model",
                    "Baseline": baseline["base_model_hash"],
                    "Controlled": controlled["base_model_hash"],
                },
                {
                    "Hash": "Derived model",
                    "Baseline": baseline["derived_model_hash"],
                    "Controlled": controlled["derived_model_hash"],
                },
                {
                    "Hash": "Weather",
                    "Baseline": baseline["weather_hash"],
                    "Controlled": controlled["weather_hash"],
                },
            ],
            hide_index=True,
            width="stretch",
        )
        streamlit.caption(
            "Report: "
            + project_relative(
                directory / "reproducibility_report.json",
                PROJECT_ROOT,
            )
        )


def _render_validity(streamlit, compatibility: dict[str, object]) -> None:
    with streamlit.expander("Comparison validity checks"):
        checks = pd.DataFrame(compatibility["checks"])[
            ["check_id", "passed", "required", "message"]
        ].rename(
            columns={
                "check_id": "Check",
                "passed": "Passed",
                "required": "Required",
                "message": "Evidence rule",
            }
        )
        streamlit.dataframe(
            checks,
            hide_index=True,
            width="stretch",
            column_config={
                "Passed": streamlit.column_config.CheckboxColumn("Passed"),
                "Required": streamlit.column_config.CheckboxColumn("Required"),
            },
        )


def _render_methodology(streamlit, summary: dict[str, object]) -> None:
    with streamlit.expander("Methodology, assumptions, and scope"):
        streamlit.markdown(
            """
- Both runs use EnergyPlus 26.1.0, the same base and derived model hashes,
  identical weather, the same annual run period, and 8,760 aligned hourly intervals.
- The controlled experiment changes only the verified `SPACE1-1` cooling
  setpoint. It is a conservative single-zone proof of concept, not a
  whole-building optimization result.
- The Phase 10 reproducibility run uses a deterministic policy. The local
  Qwen model is demonstrated separately as an advisory planner and never
  receives direct actuator authority.
- The final authority is the deterministic safety supervisor. Approved
  actions are bounded, rate-limited, verified against observed actuator
  state, and reset through documented fallback behavior.
- Genuine PMV/PPD is unavailable from the retained People objects.
  Comfort is therefore the explicitly configured occupied-temperature proxy.
- Tariff and grid-carbon values are transparent project assumptions used
  only to derive cost and carbon from measured facility electricity.
"""
        )
        streamlit.write(
            {
                "Comparison mode": summary["comparison_mode"],
                "Tariff assumption": summary["cost_metrics"]["tariff_source"],
                "Carbon assumption": summary["carbon_metrics"][
                    "carbon_intensity_source"
                ],
            }
        )


def _render_downloads(
    streamlit,
    bundle: dict[str, object],
    directory: Path,
) -> None:
    streamlit.subheader("Phase 10 downloads")
    files = (
        ("Final summary", "final_summary.json", "application/json"),
        ("Energy comparison", "energy_comparison.csv", "text/csv"),
        ("Compatibility report", "compatibility_report.json", "application/json"),
        ("Executive summary", "executive_summary.md", "text/markdown"),
        (
            "Reproducibility report",
            "reproducibility_report.json",
            "application/json",
        ),
    )
    columns = streamlit.columns(3)
    for index, (label, filename, mime) in enumerate(files):
        path = directory / filename
        columns[index % 3].download_button(
            label,
            path.read_bytes(),
            f"phase10_{filename}",
            mime,
            key=f"phase10_download_{filename}",
            width="stretch",
        )
    columns[len(files) % 3].download_button(
        "Chart archive",
        _chart_archive(str(directory.resolve())),
        "phase10_charts.zip",
        "application/zip",
        key="phase10_download_charts",
        width="stretch",
    )
    streamlit.caption(
        "All displayed paths and downloads are constrained to project evidence. "
        "The full-row CSV artifacts are unchanged by dashboard sampling."
    )


def render_phase10(_streamlit=st) -> None:
    """Render the newest valid, reproducible Phase 10 artifact bundle."""
    directory = latest_phase10_directory(require_reproducible=True)
    if directory is None:
        _streamlit.info(
            "No valid reproducible Phase 10 comparison is available. Run the "
            "comparison and reproducibility scripts to generate official evidence.",
            icon=":material/info:",
        )
        return
    try:
        bundle = load_phase10_bundle(str(directory.resolve()))
    except (OSError, ValueError, KeyError) as exc:
        _streamlit.error(
            "The Phase 10 evidence bundle could not be loaded. The dashboard "
            "has not recalculated or replaced any result."
        )
        with _streamlit.expander("Technical diagnostics"):
            _streamlit.code(f"{type(exc).__name__}: {exc}", language="text")
        return

    summary = bundle["summary"]
    _render_claim(_streamlit, summary, directory)
    _render_kpis(_streamlit, summary)
    _render_validity(_streamlit, bundle["compatibility"])
    _render_charts(_streamlit, bundle)
    _render_meter_mapping(_streamlit)
    _render_action_impact(_streamlit, bundle)
    _render_reliability(_streamlit, bundle)
    _render_reproducibility(_streamlit, bundle, directory)
    _render_methodology(_streamlit, summary)
    _render_downloads(_streamlit, bundle, directory)


__all__ = [
    "_chart_archive",
    "_format",
    "_latest_directory",
    "_load_bundle",
    "build_action_impact_table",
    "phase10_complete",
    "render_phase10",
]
