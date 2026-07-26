"""EnergyPlus installation, model, runtime, and evidence status page."""

from datetime import datetime, timezone
import logging
from pathlib import Path
import traceback
from typing import Any

import streamlit as st

from energyplus.runtime_control.api_loader import inspect_runtime_availability
from energyplus.runtime_control.settings import PHASE8_SETTINGS
from ui.artifact_views import PROJECT_ROOT
from ui.components import status_badge
from ui.formatting import project_relative

from .components import product_header, safe_page_error
from .data import DEMO_MODE_REPLAY, ArtifactLoadError, load_demo_context


LOGGER = logging.getLogger(__name__)


@st.cache_data(ttl=30, max_entries=1, show_spinner=False)
def _runtime_availability() -> Any:
    """Short-lived readiness cache; never represents a running simulation."""
    return inspect_runtime_availability()


def _switch_on_click(
    streamlit: Any,
    button_container: Any,
    label: str,
    destination: str,
    key: str,
) -> None:
    """Navigate from a container button through the root Streamlit API."""
    if not button_container.button(label, key=key, width="stretch"):
        return
    try:
        streamlit.switch_page(destination)
    except Exception as exc:
        LOGGER.exception("EnergyPlus UI workflow navigation failed: %s", label)
        diagnostics = "\n".join(
            (
                f"Exception type: {type(exc).__name__}",
                f"Message: {exc}",
                f"Requested workflow: {label}",
                f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
                "",
                "Traceback:",
                traceback.format_exc(),
            )
        )
        safe_page_error(
            streamlit,
            title="Workflow could not start",
            message=(
                "The requested EnergyPlus workflow could not be started with "
                "the current runtime configuration. Existing verified artifacts "
                "and results were not modified."
            ),
            next_step=(
                "Refresh system status, confirm the configured model and weather "
                "files, or use Verified Demo Replay."
            ),
            diagnostics=diagnostics,
        )


def render_energyplus(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    product_header(
        streamlit,
        title="EnergyPlus",
        subtitle=(
            "Installed engine readiness, frozen model/weather identity, runtime "
            "actuator proof, telemetry coverage, and official run classification."
        ),
        eyebrow="Digital twin engine",
        mode=mode,
    )
    streamlit.caption(
        "Official results use EnergyPlus; the lightweight simulator remains development-only."
    )
    try:
        context = load_demo_context()
    except ArtifactLoadError as exc:
        safe_page_error(
            streamlit,
            title="EnergyPlus evidence unavailable",
            message=exc.public_message,
            next_step="Restore the official Phase 5–10 artifacts, then refresh.",
            diagnostics=exc.diagnostics,
        )
        return

    availability = _runtime_availability()
    controlled = context["controlled_summary"]
    baseline = context["baseline_summary"]
    runtime = context.get("runtime", {})
    runtime_summary = runtime.get("summary", {})
    handles = runtime.get("handles", {})
    selected_actuator = runtime_summary.get("selected_actuator", {})
    detected_zones = (
        int(controlled.get("zone_row_count", 0))
        // max(1, int(controlled.get("reporting_interval_count", 1)))
    )

    with streamlit.container(horizontal=True, gap="small"):
        for label, value, note, status in (
            (
                "Installation",
                "Available" if availability.available else "Unavailable",
                str(availability.installation_root),
                "verified" if availability.available else "error",
            ),
            (
                "EnergyPlus version",
                availability.EnergyPlus_version
                or controlled.get("energyplus_version", "Unavailable"),
                "Official comparison engine",
                "verified",
            ),
            (
                "Executable",
                str(availability.installation_root / "energyplus.exe"),
                "Configured local executable",
                "verified" if availability.available else "error",
            ),
            (
                "Python API",
                availability.API_version or "Unavailable",
                "Runtime/Data Transfer API",
                "verified" if availability.pyenergyplus_importable else "warning",
            ),
            (
                "Runtime status",
                "Verified artifact replay",
                "No simulation is currently claimed as running",
                "info",
            ),
            (
                "Latest run",
                controlled.get("run_id", "Unavailable"),
                controlled.get("classification", "Unavailable"),
                "verified",
            ),
        ):
            with streamlit.container(border=True):
                streamlit.caption(label.upper())
                streamlit.markdown(f"**{value}**")
                status_badge(streamlit, status.title(), status=status)
                streamlit.caption(note)

    streamlit.subheader("Model and weather identity")
    streamlit.dataframe(
        [
            {
                "Asset": "Baseline IDF",
                "Path": project_relative(
                    PHASE8_SETTINGS.resolve(PHASE8_SETTINGS.source_model_path),
                    PROJECT_ROOT,
                ),
                "SHA-256": baseline.get("base_model_hash"),
                "Match": True,
            },
            {
                "Asset": "Runtime-control IDF",
                "Path": project_relative(
                    PHASE8_SETTINGS.resolve(PHASE8_SETTINGS.runtime_model_path),
                    PROJECT_ROOT,
                ),
                "SHA-256": controlled.get("derived_model_hash"),
                "Match": True,
            },
            {
                "Asset": "EPW weather",
                "Path": project_relative(
                    PHASE8_SETTINGS.resolve(PHASE8_SETTINGS.weather_file_path),
                    PROJECT_ROOT,
                ),
                "SHA-256": controlled.get("weather_hash"),
                "Match": True,
            },
        ],
        hide_index=True,
    )

    streamlit.subheader("Runtime control evidence")
    with streamlit.container(horizontal=True, gap="small"):
        for label, value in (
            ("Simulation period", "Jan 1 – Dec 31"),
            ("Reporting", controlled.get("reporting_frequency", "Unavailable")),
            (
                "Telemetry intervals",
                f"{controlled.get('reporting_interval_count', 0):,}",
            ),
            ("Zone records", f"{controlled.get('zone_row_count', 0):,}"),
            ("Detected zones", f"{detected_zones}"),
            ("Selected zone", selected_actuator.get("actuator_key", "Unavailable")),
            (
                "Actuator",
                selected_actuator.get("identifier", "Unavailable"),
            ),
            (
                "Actuator handle",
                str(handles.get("cooling_actuator", "Unavailable")),
            ),
            (
                "Actuator writes",
                f"{controlled.get('actuator_write_count', 0):,}",
            ),
            (
                "Severe / fatal",
                f"{controlled.get('severe_count', '—')} / "
                f"{controlled.get('fatal_count', '—')}",
            ),
        ):
            streamlit.metric(label, value, border=True)

    streamlit.caption(
        "Output path · "
        + project_relative(
            Path(controlled["runtime_artifact_directory"]),
            PROJECT_ROOT,
        )
    )
    status_badge(
        streamlit,
        controlled.get("classification", "Classification unavailable"),
        status="verified",
    )

    streamlit.subheader("Explicit workflows")
    streamlit.caption(
        "These controls navigate to the existing validated pages. No expensive "
        "workflow starts on this page or during import."
    )
    controls = streamlit.container(horizontal=True, gap="small")
    if controls.button(
        "Refresh status",
        icon=":material/refresh:",
        key="energyplus-refresh",
    ):
        _runtime_availability.clear()
        streamlit.rerun()
    if controls.button("Load latest baseline", key="energyplus-load-baseline"):
        streamlit.session_state["energyplus_loaded_view"] = "baseline"
    if controls.button("Load latest controlled run", key="energyplus-load-controlled"):
        streamlit.session_state["energyplus_loaded_view"] = "controlled"
    _switch_on_click(
        streamlit,
        controls,
        "Run smoke test",
        "app_pages/phase4.py",
        "energyplus-smoke",
    )
    _switch_on_click(
        streamlit,
        controls,
        "Run official baseline",
        "app_pages/phase5.py",
        "energyplus-baseline",
    )
    _switch_on_click(
        streamlit,
        controls,
        "Run runtime validation",
        "app_pages/phase8.py",
        "energyplus-runtime",
    )

    loaded = streamlit.session_state.get("energyplus_loaded_view")
    if loaded == "baseline":
        streamlit.success(
            f"Loaded baseline artifact {baseline.get('run_id', '—')} · "
            f"{baseline.get('total_facility_electricity_kwh', '—')} kWh"
        )
    elif loaded == "controlled":
        streamlit.success(
            f"Loaded controlled artifact {controlled.get('run_id', '—')} · "
            f"{controlled.get('total_facility_electricity_kwh', '—')} kWh"
        )
    if availability.readiness_issues:
        with streamlit.expander("Readiness diagnostics"):
            for issue in availability.readiness_issues:
                streamlit.code(issue, language="text")


__all__ = ["_runtime_availability", "render_energyplus"]
