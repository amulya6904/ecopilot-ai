"""Streamlit presentation for the implemented local Phase 6 MCP layer."""

from importlib.metadata import version
from pathlib import Path
import subprocess
import sys
from typing import Any

import pandas as pd

from mcp_service.audit import AuditLogger
from mcp_service.resources import RESOURCE_CATALOGUE
from mcp_service.settings import MCP_SETTINGS


TOOL_CATALOGUE = (
    ("get_system_status", "system", "read-only", "Project, backend, MCP, and audit status", "none", "status object"),
    ("get_energyplus_readiness", "system", "read-only", "Phase 4 EnergyPlus readiness", "none", "readiness object"),
    ("get_phase_status", "system", "read-only", "Honest phase status", "none", "phase list"),
    ("get_available_outputs", "system", "read-only", "Available EnergyPlus outputs", "none", "availability map"),
    ("get_official_baseline_summary", "baseline", "read-only", "Persisted official baseline metrics", "none", "summary object"),
    ("get_baseline_manifest", "baseline", "read-only", "Frozen hashes and configuration", "none", "sanitized manifest"),
    ("get_latest_energyplus_run", "baseline", "read-only", "Latest official run metadata", "none", "compact metadata"),
    ("run_official_baseline", "baseline", "execution", "Controlled Phase 5 runner invocation", "two booleans", "compact run result"),
    ("list_zones", "zones", "read-only", "Technical names, aliases, and roles", "none", "zone list"),
    ("get_zone_summary", "zones", "read-only", "One persisted zone summary", "zone name", "zone metrics"),
    ("get_zone_telemetry", "zones", "read-only", "Bounded zone telemetry", "zone, dates, aggregation, limit", "bounded records"),
    ("get_facility_summary", "facility", "read-only", "Whole-facility metrics", "none", "facility metrics"),
    ("get_facility_telemetry", "facility", "read-only", "Bounded facility telemetry", "dates, aggregation, limit", "bounded records"),
    ("get_comfort_summary", "comfort", "read-only", "Temperature and PMV availability", "none", "comfort metrics"),
    ("get_thermostat_adherence", "comfort", "read-only", "Frozen policy adherence", "none", "adherence and samples"),
    ("get_runtime_errors", "diagnostics", "read-only", "Bounded EnergyPlus diagnostics", "severity, classification, limit", "compact records"),
)


def render_phase6(st: Any) -> None:
    st.caption(
        "Local official-SDK stdio server exposing verified EnergyPlus and official "
        "baseline capabilities. It has no LLM, actuator, optimization, or control tools."
    )
    audit = AuditLogger(MCP_SETTINGS.resolve(MCP_SETTINGS.audit_log_path))
    cards = st.columns(4)
    cards[0].metric("Server", MCP_SETTINGS.server_name)
    cards[1].metric("MCP SDK", version("mcp"))
    cards[2].metric("Transport", MCP_SETTINGS.protocol_transport)
    cards[3].metric("Tools / resources", f"{len(TOOL_CATALOGUE)} / {len(RESOURCE_CATALOGUE)}")
    st.json({
        "read_only_default": MCP_SETTINGS.read_only_default,
        "baseline_run_tool_enabled": MCP_SETTINGS.baseline_run_tool_enabled,
        "control_tools_enabled": False,
        "audit_log_status": "available" if audit.last_error is None else "degraded",
    })
    st.subheader("Tool catalogue")
    st.dataframe(
        pd.DataFrame(
            TOOL_CATALOGUE,
            columns=("name", "category", "mode", "description", "input schema", "output"),
        ),
        hide_index=True,
        width="stretch",
    )
    st.subheader("Read-only resource catalogue")
    st.dataframe(pd.DataFrame(RESOURCE_CATALOGUE), hide_index=True, width="stretch")
    if st.button("Run MCP Client Smoke Test", type="primary"):
        with st.spinner("Starting a separate stdio server and official SDK client..."):
            try:
                completed = subprocess.run(
                    [sys.executable, "-m", "scripts.test_phase6_mcp_client"],
                    cwd=Path(__file__).parents[1],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                    shell=False,
                )
                if completed.returncode == 0:
                    st.success("MCP client smoke test passed.")
                else:
                    st.error("MCP client smoke test failed.")
                st.code(completed.stdout or completed.stderr, language="text")
            except subprocess.TimeoutExpired:
                st.error("MCP client smoke test exceeded 120 seconds.")
    st.subheader("Latest audit entries")
    entries = audit.latest(20)
    if entries:
        st.dataframe(pd.DataFrame(entries), hide_index=True, width="stretch")
    else:
        st.info("No audited MCP tool calls have been recorded yet.")


__all__ = ["TOOL_CATALOGUE", "render_phase6"]
