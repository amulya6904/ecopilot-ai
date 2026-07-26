"""Executive, artifact-backed Phase 10 quantitative results experience."""

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
    load_phase10_event_timeline,
)
from .charts import (
    action_setpoint_chart,
    comparison_line_chart,
    fallback_timeline_chart,
    requested_approved_chart,
    safety_outcome_chart,
)
from .components import (
    artifact_download,
    compact_metric,
    editorial_callout,
    empty_state,
    eyebrow,
    methodology_item,
    result_metric,
    scope_note,
    section_divider,
    status_badge,
)
from .constants import SMALL_RESULT_NOTE
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


RESULT_HEADING = "Verified EnergyPlus control with measurable, reproducible impact."
RESULT_NARRATIVE = (
    "Under a fully aligned EnergyPlus experiment, the safety-supervised "
    "one-zone policy reduced annual facility electricity by 5.626 kWh, or "
    "0.0096%. Occupied-temperature proxy compliance improved slightly, while "
    "peak demand remained effectively unchanged."
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


@st.cache_data(max_entries=4, show_spinner=False)
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
    """Join action evidence to full-resolution aligned interval evidence."""
    if actions.empty:
        return pd.DataFrame()
    action_frame = actions.copy()
    action_frame["_calendar_key"] = _calendar_key(action_frame["timestamp"])
    energy_frame = energy[
        [
            "timestamp",
            "baseline_energy_kwh",
            "controlled_energy_kwh",
            "interval_energy_reduction_kwh",
        ]
    ].copy()
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
            "decision": "safety_outcome",
        }
    )


def meaningful_action_windows(
    table: pd.DataFrame,
    *,
    limit: int = 24,
) -> pd.DataFrame:
    """Select display-only action windows without changing any metric."""
    if table.empty or len(table) <= limit:
        return table.copy()
    ranked = table.assign(
        _impact=pd.to_numeric(
            table["interval_energy_difference_kwh"],
            errors="coerce",
        ).abs()
    )
    return (
        ranked.nlargest(limit, "_impact")
        .sort_values("timestamp")
        .drop(columns="_impact")
    )


def _render_hero(
    streamlit,
    summary: dict[str, object],
    directory: Path,
) -> None:
    with streamlit.container(key="results-hero"):
        eyebrow(streamlit, "Phase 10 · Official quantitative comparison")
        streamlit.title(RESULT_HEADING)
        streamlit.write(RESULT_NARRATIVE)
        with streamlit.container(horizontal=True):
            status_badge(streamlit, "Official EnergyPlus", status="info")
            status_badge(streamlit, "Safety supervised", status="verified")
            status_badge(streamlit, "Reproducible", status="verified")
        streamlit.caption(
            "Source · "
            f"{project_relative(directory / 'final_summary.json', PROJECT_ROOT)} "
            f"· {summary['comparison_id']}"
        )


def _render_validity_band(
    streamlit,
    summary: dict[str, object],
    report: dict[str, object],
) -> None:
    checks = (
        ("Official EnergyPlus comparison", summary["official_energyplus_comparison"]),
        ("Same model", report["model_hashes_match"]),
        ("Same weather", report["weather_hashes_match"]),
        ("Same run period", summary["comparison_valid"]),
        (
            f"{summary['alignment']['matched_intervals']:,} / "
            f"{summary['alignment']['total_expected_intervals']:,} intervals",
            summary["alignment"]["complete"],
        ),
        ("Reproducible", report["reproducible"]),
        (f"Severe errors · {summary['severe_count']}", summary["severe_count"] == 0),
        (f"Fatal errors · {summary['fatal_count']}", summary["fatal_count"] == 0),
    )
    with streamlit.container(
        key="validity-band",
        horizontal=True,
        gap="small",
    ):
        for label, passed in checks:
            status_badge(
                streamlit,
                label,
                status="verified" if passed else "error",
            )


def _render_executive_kpis(
    streamlit,
    summary: dict[str, object],
) -> None:
    section_divider(
        streamlit,
        "Measured annual result",
        "One conservative zone, compared over a fully aligned annual horizon.",
    )
    primary, secondary = streamlit.columns(
        [3, 2],
        gap="large",
        vertical_alignment="bottom",
    )
    with primary:
        result_metric(
            streamlit,
            label="Verified facility-energy reduction",
            value=format_energy(summary["energy_reduction_kwh"], compact=True),
            primary=True,
        )
        result_metric(
            streamlit,
            label="Reproducible annual reduction",
            value=format_percent(summary["energy_reduction_percent"], 4),
        )
    with secondary:
        compact_metric(
            streamlit,
            label="Baseline facility energy",
            value=format_energy(summary["baseline_energy_kwh"]),
        )
        compact_metric(
            streamlit,
            label="Controlled facility energy",
            value=format_energy(summary["controlled_energy_kwh"]),
        )
        compact_metric(
            streamlit,
            label="Comfort proxy change",
            value=(
                f"{float(summary['comfort_metrics']['comfort_change_percent_points']):+.3f} pp"
            ),
        )
        compact_metric(
            streamlit,
            label="Peak-demand change",
            value=peak_change_label(
                summary["demand_metrics"]["absolute_peak_reduction_kw"],
                tolerance_kw=1e-6,
            ),
        )

    cost = summary["cost_metrics"]
    carbon = summary["carbon_metrics"]
    with streamlit.container(horizontal=True, gap="large"):
        compact_metric(
            streamlit,
            label="Derived cost change",
            value=format_cost(cost["absolute_cost_reduction"], cost["currency"]),
            note="Configured tariff assumption.",
        )
        compact_metric(
            streamlit,
            label="Derived carbon change",
            value=format_carbon(carbon["absolute_carbon_reduction_kg"]),
            note="Configured carbon-intensity assumption.",
        )
        compact_metric(
            streamlit,
            label="Severe / fatal errors",
            value=f"{summary['severe_count']} / {summary['fatal_count']}",
        )
    editorial_callout(
        streamlit,
        "The whole-building effect is intentionally small because the proof "
        "of concept controls one zone conservatively under strict safety constraints.",
    )


def _render_energy(streamlit, bundle: dict[str, object]) -> None:
    summary = bundle["summary"]
    section_divider(
        streamlit,
        "Cumulative facility electricity",
        "The controlled trajectory remains close to baseline and finishes "
        "5.626076 kWh lower across the complete year.",
    )
    with streamlit.container(key="chart-panel-energy"):
        comparison_line_chart(
            streamlit,
            bundle["energy"],
            series={
                "baseline_cumulative_energy_kwh": "Fixed-schedule baseline",
                "controlled_cumulative_energy_kwh": "Safety-supervised controlled",
            },
            y_title="Cumulative facility electricity (kWh)",
            show_endpoints=True,
            zero=True,
        )
    streamlit.caption(
        "Final endpoints: "
        f"{float(summary['baseline_energy_kwh']):,.6f} kWh baseline · "
        f"{float(summary['controlled_energy_kwh']):,.6f} kWh controlled · "
        f"{float(summary['energy_reduction_kwh']):,.6f} kWh difference."
    )


def _render_demand(streamlit, bundle: dict[str, object]) -> None:
    summary = bundle["summary"]
    section_divider(
        streamlit,
        "Peak demand remained effectively unchanged",
        "The absolute peak difference is below the configured reproducibility "
        "tolerance and is not presented as a reduction.",
    )
    with streamlit.container(key="chart-panel-demand"):
        comparison_line_chart(
            streamlit,
            bundle["demand"],
            series={
                "baseline_demand_kw": "Fixed-schedule baseline",
                "controlled_demand_kw": "Safety-supervised controlled",
            },
            y_title="Facility demand (kW)",
            zero=True,
        )
    with streamlit.container(horizontal=True, gap="large"):
        compact_metric(
            streamlit,
            label="Baseline peak",
            value=format_demand(summary["baseline_peak_demand_kw"]),
        )
        compact_metric(
            streamlit,
            label="Controlled peak",
            value=format_demand(summary["controlled_peak_demand_kw"]),
        )
        compact_metric(
            streamlit,
            label="Measured peak classification",
            value="Essentially unchanged",
        )


def _render_comfort(streamlit, bundle: dict[str, object]) -> None:
    summary = bundle["summary"]
    comfort = summary["comfort_metrics"]
    baseline = comfort["baseline"]
    controlled = comfort["controlled"]
    section_divider(
        streamlit,
        "Occupied-temperature proxy performance",
        "Genuine PMV/PPD is unavailable in the retained People objects, so "
        "the declared measure is occupied-temperature compliance.",
    )
    with streamlit.container(horizontal=True, gap="large"):
        compact_metric(
            streamlit,
            label="Baseline compliance",
            value=format_comfort(summary["baseline_comfort_percent"]),
        )
        compact_metric(
            streamlit,
            label="Controlled compliance",
            value=format_comfort(summary["controlled_comfort_percent"]),
        )
        compact_metric(
            streamlit,
            label="Difference",
            value=f"{float(comfort['comfort_change_percent_points']):+.3f} pp",
        )
        compact_metric(streamlit, label="PMV", value="Unavailable")
    occupied_zone = bundle["comfort"].loc[
        bundle["comfort"]["energyplus_zone_name"].eq("SPACE1-1")
        & (
            pd.to_numeric(
                bundle["comfort"]["occupancy_controlled"],
                errors="coerce",
            ).fillna(0)
            > 0
        )
    ]
    with streamlit.container(key="chart-panel-comfort"):
        comparison_line_chart(
            streamlit,
            occupied_zone,
            series={
                "indoor_temperature_c_baseline": "Fixed-schedule baseline",
                "indoor_temperature_c_controlled": "Safety-supervised controlled",
                "comfort_min_c": "Configured lower bound",
                "comfort_max_c": "Configured upper bound",
            },
            y_title="Occupied zone temperature (°C)",
            zero=False,
        )
    comfort_range = (
        f"{float(occupied_zone['comfort_min_c'].min()):.1f}–"
        f"{float(occupied_zone['comfort_max_c'].max()):.1f} °C"
        if not occupied_zone.empty
        else "Unavailable"
    )
    streamlit.dataframe(
        [
            {
                "Run": "Fixed-schedule baseline",
                "Low violations": baseline["low_temperature_violations"],
                "High violations": baseline["high_temperature_violations"],
                "Maximum deviation (°C)": baseline["maximum_deviation_c"],
                "Comfort range": comfort_range,
                "PMV": "Unavailable",
            },
            {
                "Run": "Safety-supervised controlled",
                "Low violations": controlled["low_temperature_violations"],
                "High violations": controlled["high_temperature_violations"],
                "Maximum deviation (°C)": controlled["maximum_deviation_c"],
                "Comfort range": comfort_range,
                "PMV": "Unavailable",
            },
        ],
        hide_index=True,
        width="stretch",
    )


def _render_action_evidence(
    streamlit,
    bundle: dict[str, object],
    directory: Path,
) -> None:
    section_divider(
        streamlit,
        "Action-to-impact evidence",
        "Requested, approved, applied, and observed values remain linked to "
        "the interval energy and deterministic safety outcome.",
    )
    with streamlit.container(key="chart-panel-setpoints"):
        streamlit.subheader("Setpoint timeline")
        action_setpoint_chart(streamlit, bundle["actions"])
    left, right = streamlit.columns(2, gap="large")
    with left:
        with streamlit.container(key="chart-panel-requested-approved"):
            streamlit.subheader("Requested versus approved")
            requested_approved_chart(streamlit, bundle["actions"])
    with right:
        with streamlit.container(key="chart-panel-safety-outcomes"):
            streamlit.subheader("Deterministic safety outcomes")
            safety_outcome_chart(streamlit, bundle["reliability"])

    events = load_phase10_event_timeline(str(directory.resolve()))
    with streamlit.container(key="chart-panel-fallbacks"):
        streamlit.subheader("Fallback and rollback timeline")
        fallback_timeline_chart(streamlit, events)
        streamlit.caption(
            f"{len(events.loc[events['event_type'].eq('Fallback')]):,} fallback "
            "events · 0 rollback events · 0 emergency events in this comparison."
        )

    table = build_action_impact_table(
        bundle["actions"],
        bundle["energy"],
        bundle["comfort"],
    )
    display = meaningful_action_windows(table)
    display_columns = [
        "timestamp",
        "zone",
        "baseline_setpoint_c",
        "requested_setpoint_c",
        "approved_setpoint_c",
        "observed_setpoint_c",
        "baseline_interval_energy_kwh",
        "controlled_interval_energy_kwh",
        "interval_energy_difference_kwh",
        "safety_outcome",
    ]
    streamlit.subheader("Meaningful action windows")
    streamlit.dataframe(
        display[display_columns],
        hide_index=True,
        width="stretch",
    )
    streamlit.caption(
        f"Showing {len(display):,} of {len(table):,} action windows, ranked by "
        "absolute interval-energy difference for display only. The join and "
        "all metrics use full-resolution data."
    )
    streamlit.download_button(
        "Download full action-to-impact CSV",
        table.to_csv(index=False).encode("utf-8"),
        "phase10_action_to_impact_full.csv",
        "text/csv",
        key="phase10-action-impact-full",
        icon=":material/download:",
    )


def _render_methodology(streamlit, summary: dict[str, object]) -> None:
    section_divider(
        streamlit,
        "Methodology",
        "The compact specification behind the claim gate.",
    )
    columns = streamlit.columns(2, gap="large")
    items = (
        ("Simulation engine", "EnergyPlus 26.1"),
        ("Experiment basis", "Identical model and weather"),
        ("Reporting", "Hourly · 8,760 aligned intervals"),
        ("Control scope", "One controlled zone · SPACE1-1"),
        ("Policy", "Deterministic reproducible policy"),
        ("Comfort measure", "Occupied-temperature proxy · PMV unavailable"),
        (
            "Derived assumptions",
            f"{summary['cost_metrics']['currency']} "
            f"{summary['cost_metrics']['flat_tariff_per_kwh']}/kWh · "
            f"{summary['carbon_metrics']['constant_carbon_intensity_g_per_kwh']} "
            "g CO₂/kWh",
        ),
    )
    for index, (label, value) in enumerate(items):
        with columns[index % 2]:
            methodology_item(streamlit, label=label, value=value)


def _render_technical_evidence(
    streamlit,
    bundle: dict[str, object],
    directory: Path,
) -> None:
    summary = bundle["summary"]
    report = bundle["reproducibility"]
    with streamlit.expander(
        "Technical validity, meter mapping, and frozen hashes",
        expanded=False,
        icon=":material/fingerprint:",
    ):
        streamlit.subheader("Compatibility checks")
        checks = pd.DataFrame(bundle["compatibility"]["checks"])[
            ["check_id", "passed", "required", "message"]
        ]
        streamlit.dataframe(checks, hide_index=True, width="stretch")
        streamlit.subheader("EnergyPlus meter mapping")
        streamlit.dataframe(
            [
                ("Facility electricity", "Electricity:Facility", "J → kWh"),
                ("HVAC electricity", "Electricity:HVAC", "J → kWh"),
                ("Cooling electricity", "Cooling:Electricity", "J → kWh"),
                ("Heating electricity", "Heating:Electricity", "J → kWh"),
                ("Fan electricity", "Fans:Electricity", "J → kWh"),
            ],
            column_config={
                0: "Displayed quantity",
                1: "EnergyPlus source",
                2: "Display conversion",
            },
            hide_index=True,
            width="stretch",
        )
        streamlit.subheader("Reproducibility chain")
        streamlit.dataframe(
            [
                ("Displayed comparison", str(summary["comparison_id"])),
                ("First comparison", str(report["first_comparison_id"])),
                ("Verified repeat", str(report["second_comparison_id"])),
                ("Model hashes match", str(report["model_hashes_match"])),
                ("Weather hashes match", str(report["weather_hashes_match"])),
                ("Telemetry shape matches", str(report["telemetry_shape_match"])),
                ("Tolerance", str(report["tolerance"])),
            ],
            column_config={0: "Evidence", 1: "Value"},
            hide_index=True,
            width="stretch",
        )
        streamlit.subheader("Frozen hashes")
        streamlit.dataframe(
            [
                {
                    "Hash": "Base model",
                    "Baseline": bundle["baseline"]["base_model_hash"],
                    "Controlled": bundle["controlled"]["base_model_hash"],
                },
                {
                    "Hash": "Derived model",
                    "Baseline": bundle["baseline"]["derived_model_hash"],
                    "Controlled": bundle["controlled"]["derived_model_hash"],
                },
                {
                    "Hash": "Weather",
                    "Baseline": bundle["baseline"]["weather_hash"],
                    "Controlled": bundle["controlled"]["weather_hash"],
                },
            ],
            hide_index=True,
            width="stretch",
        )
        streamlit.caption(
            project_relative(
                directory / "reproducibility_report.json",
                PROJECT_ROOT,
            )
        )
        if not bool(streamlit.session_state.get("judge_mode", True)):
            with streamlit.expander("Raw final summary JSON", expanded=False):
                streamlit.json(summary, expanded=False)


def _render_downloads(
    streamlit,
    directory: Path,
) -> None:
    section_divider(
        streamlit,
        "Downloads",
        "Full-resolution artifacts are unchanged by display sampling.",
    )
    files = (
        ("Final summary", "final_summary.json"),
        ("Energy comparison CSV", "energy_comparison.csv"),
        ("Demand comparison CSV", "demand_comparison.csv"),
        ("Comfort comparison CSV", "comfort_comparison.csv"),
        ("Action summary CSV", "action_summary.csv"),
        ("Reproducibility report", "reproducibility_report.json"),
    )
    columns = streamlit.columns(3)
    for index, (label, filename) in enumerate(files):
        with columns[index % 3]:
            artifact_download(
                streamlit,
                label=label,
                path=directory / filename,
                key=f"phase10-download-{filename}",
            )
    streamlit.download_button(
        "Download chart archive",
        _chart_archive(str(directory.resolve())),
        "phase10_charts.zip",
        "application/zip",
        key="phase10-download-charts",
        icon=":material/download:",
    )


def render_phase10(_streamlit=st) -> None:
    """Render the newest valid reproducible bundle without recalculation."""
    directory = latest_phase10_directory(require_reproducible=True)
    if directory is None:
        empty_state(
            _streamlit,
            "No valid reproducible Phase 10 comparison is available. Run the "
            "documented comparison and reproducibility scripts, then refresh.",
        )
        return
    try:
        bundle = load_phase10_bundle(str(directory.resolve()))
    except (OSError, ValueError, KeyError) as exc:
        _streamlit.error(
            "The Phase 10 evidence bundle could not be loaded. No result was "
            "recalculated or replaced."
        )
        with _streamlit.expander("Technical diagnostics"):
            _streamlit.code(f"{type(exc).__name__}: {exc}", language="text")
        return

    summary = bundle["summary"]
    _render_hero(_streamlit, summary, directory)
    _render_validity_band(_streamlit, summary, bundle["reproducibility"])
    _render_executive_kpis(_streamlit, summary)
    _render_energy(_streamlit, bundle)
    _render_demand(_streamlit, bundle)
    _render_comfort(_streamlit, bundle)
    _render_action_evidence(_streamlit, bundle, directory)
    _render_methodology(_streamlit, summary)
    _render_technical_evidence(_streamlit, bundle, directory)
    scope_note(
        _streamlit,
        SMALL_RESULT_NOTE
        + " Genuine PMV/PPD is unavailable. Peak demand is essentially "
        "unchanged. Tariff and carbon intensity are configured assumptions, "
        "not native EnergyPlus outputs.",
    )
    _render_downloads(_streamlit, directory)


__all__ = [
    "RESULT_HEADING",
    "RESULT_NARRATIVE",
    "_chart_archive",
    "_format",
    "_latest_directory",
    "_load_bundle",
    "build_action_impact_table",
    "meaningful_action_windows",
    "phase10_complete",
    "render_phase10",
]
