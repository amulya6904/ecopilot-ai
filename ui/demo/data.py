"""Project-scoped, cached artifact adapters for the Phase 12 demo UI."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st

from ui.artifact_views import (
    DOCS_ROOT,
    PHASE10_ROOT,
    PROJECT_ROOT,
    RESULTS_ROOT,
    is_approved_display_path,
    latest_phase10_directory,
)


CONTROLLED_ZONE = "SPACE1-1"
DEMO_MODE_REPLAY = "Verified Demo Replay"
DEMO_MODE_LIVE = "Live Services"

COMPARISON_CSV_FILES = frozenset(
    {
        "action_summary.csv",
        "aligned_facility_telemetry.csv",
        "aligned_zone_telemetry.csv",
        "carbon_comparison.csv",
        "comfort_comparison.csv",
        "cost_comparison.csv",
        "demand_comparison.csv",
        "energy_comparison.csv",
    }
)


class ArtifactLoadError(RuntimeError):
    """A safe UI-facing wrapper for missing or malformed persisted evidence."""

    def __init__(self, message: str, *, diagnostics: str | None = None):
        super().__init__(message)
        self.public_message = message
        self.diagnostics = diagnostics or message


@dataclass(frozen=True)
class DemoArtifactIndex:
    comparison: Path
    phase7: Path | None
    safety: Path | None
    runtime: Path | None
    llm_runtime: Path | None


def _inside(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    approved = root.resolve()
    return resolved == approved or approved in resolved.parents


def _approved_result_path(path: Path) -> Path:
    resolved = path.resolve()
    if not _inside(resolved, RESULTS_ROOT):
        raise ArtifactLoadError(
            "Artifact access was blocked because it is outside the approved results directory.",
            diagnostics=str(resolved),
        )
    return resolved


def _fingerprint(path: Path) -> tuple[str, int, int]:
    resolved = path.resolve()
    stat = resolved.stat()
    return str(resolved), stat.st_mtime_ns, stat.st_size


@st.cache_data(max_entries=64, show_spinner=False)
def _read_json_cached(
    path_text: str,
    modified_ns: int,
    size: int,
) -> Any:
    del modified_ns, size
    return json.loads(Path(path_text).read_text(encoding="utf-8"))


def load_json(path: Path, *, default: Any = None) -> Any:
    """Load one project-scoped JSON artifact with mtime/size invalidation."""
    try:
        resolved = _approved_result_path(path)
        if not resolved.is_file():
            if default is not None:
                return default
            raise ArtifactLoadError(f"Required artifact is unavailable: {resolved.name}")
        return _read_json_cached(*_fingerprint(resolved))
    except ArtifactLoadError:
        raise
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        if default is not None:
            return default
        raise ArtifactLoadError(
            f"Artifact could not be read safely: {Path(path).name}",
            diagnostics=f"{type(exc).__name__}: {exc}",
        ) from exc


@st.cache_data(max_entries=40, show_spinner=False)
def _read_csv_cached(
    path_text: str,
    modified_ns: int,
    size: int,
    usecols: tuple[str, ...],
) -> pd.DataFrame:
    del modified_ns, size
    return pd.read_csv(Path(path_text), usecols=list(usecols) or None)


@st.cache_data(max_entries=24, show_spinner=False)
def _read_bytes_cached(
    path_text: str,
    modified_ns: int,
    size: int,
) -> bytes:
    del modified_ns, size
    return Path(path_text).read_bytes()


def load_approved_file_bytes(path: Path) -> bytes:
    """Read a download only from the repository's approved evidence roots."""
    resolved = Path(path).resolve()
    if not is_approved_display_path(resolved) or not resolved.is_file():
        raise ArtifactLoadError(
            "Download access was blocked or the artifact is unavailable.",
            diagnostics=str(resolved),
        )
    try:
        return _read_bytes_cached(*_fingerprint(resolved))
    except OSError as exc:
        raise ArtifactLoadError(
            f"Download could not be read safely: {resolved.name}",
            diagnostics=f"{type(exc).__name__}: {exc}",
        ) from exc


def load_csv(path: Path, *, usecols: Iterable[str] = ()) -> pd.DataFrame:
    """Load approved CSV evidence once; filtering remains outside the cache."""
    try:
        resolved = _approved_result_path(path)
        if not resolved.is_file():
            raise ArtifactLoadError(f"Required telemetry is unavailable: {resolved.name}")
        return _read_csv_cached(
            *_fingerprint(resolved),
            tuple(usecols),
        )
    except ArtifactLoadError:
        raise
    except (OSError, ValueError, TypeError, pd.errors.ParserError) as exc:
        raise ArtifactLoadError(
            f"Telemetry could not be read safely: {Path(path).name}",
            diagnostics=f"{type(exc).__name__}: {exc}",
        ) from exc


def _latest_directory(
    root: Path,
    required_file: str,
    *,
    predicate: Any = None,
) -> Path | None:
    if not root.is_dir():
        return None
    candidates = sorted(
        (
            item
            for item in root.iterdir()
            if item.is_dir() and (item / required_file).is_file()
        ),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for directory in candidates:
        if predicate is None:
            return directory
        try:
            if predicate(load_json(directory / required_file)):
                return directory
        except ArtifactLoadError:
            continue
    return None


def latest_phase7_directory() -> Path | None:
    return _latest_directory(
        RESULTS_ROOT / "agent" / "phase7",
        "run_metadata.json",
        predicate=lambda value: bool(value.get("success")),
    )


def latest_safety_directory() -> Path | None:
    return _latest_directory(
        RESULTS_ROOT / "safety" / "phase9",
        "run_metadata.json",
        predicate=lambda value: bool(value.get("acceptance_checks_passed")),
    )


def latest_llm_runtime_directory() -> Path | None:
    return _latest_directory(
        RESULTS_ROOT / "closed_loop" / "phase8",
        "summary.json",
        predicate=lambda value: bool(
            value.get("success")
            and value.get("mode") == "phase7_llm"
            and value.get("real_llm_used")
        ),
    )


def latest_artifact_index() -> DemoArtifactIndex:
    comparison = latest_phase10_directory(require_reproducible=True)
    if comparison is None:
        raise ArtifactLoadError(
            "No valid reproducible Phase 10 comparison is available.",
            diagnostics=(
                "Run scripts.run_phase10_comparison and "
                "scripts.verify_phase10_reproducibility."
            ),
        )
    controlled = load_json(comparison / "controlled_summary.json")
    runtime_text = controlled.get("runtime_artifact_directory")
    runtime = (
        _approved_result_path(Path(runtime_text))
        if isinstance(runtime_text, str) and runtime_text
        else None
    )
    return DemoArtifactIndex(
        comparison=comparison.resolve(),
        phase7=latest_phase7_directory(),
        safety=latest_safety_directory(),
        runtime=runtime,
        llm_runtime=latest_llm_runtime_directory(),
    )


def load_demo_context(index: DemoArtifactIndex | None = None) -> dict[str, Any]:
    """Load compact Phase 12 metadata without loading annual telemetry."""
    selected = index or latest_artifact_index()
    comparison = selected.comparison
    names = (
        "final_summary.json",
        "compatibility_report.json",
        "reproducibility_report.json",
        "baseline_summary.json",
        "controlled_summary.json",
        "reliability_metrics.json",
        "safety_metrics.json",
        "agent_metrics.json",
        "comparison_manifest.json",
    )
    context: dict[str, Any] = {
        "index": selected,
        **{
            Path(name).stem: load_json(comparison / name)
            for name in names
        },
    }
    context["summary"] = context["final_summary"]

    context["phase7"] = {}
    if selected.phase7:
        context["phase7"] = {
            "metadata": load_json(selected.phase7 / "run_metadata.json"),
            "proposal": load_json(selected.phase7 / "proposal.json", default={}),
            "decision": load_json(selected.phase7 / "llm_decision.json", default={}),
            "tools": load_json(selected.phase7 / "tool_calls.json", default=[]),
            "validation": load_json(selected.phase7 / "validation.json", default={}),
        }

    context["safety_run"] = {}
    if selected.safety:
        context["safety_run"] = {
            "metadata": load_json(selected.safety / "run_metadata.json"),
            "summary": load_json(selected.safety / "summary.json", default={}),
            "faults": load_json(
                selected.safety / "fault_injection_results.json",
                default=[],
            ),
            "decisions": load_json(
                selected.safety / "safety_decisions.json",
                default=[],
            ),
            "proposals": load_json(
                selected.safety / "proposed_actions.json",
                default=[],
            ),
            "post_action": load_json(
                selected.safety / "post_action_verification.json",
                default=[],
            ),
        }

    context["runtime"] = {}
    if selected.runtime:
        context["runtime"] = {
            "summary": load_json(selected.runtime / "summary.json", default={}),
            "handles": load_json(
                selected.runtime / "handle_registry.json",
                default={},
            ),
            "fallbacks": load_json(
                selected.runtime / "fallback_events.json",
                default=[],
            ),
            "rollbacks": load_json(
                selected.runtime / "controlled_rollback_events.json",
                default=[],
            ),
            "emergencies": load_json(
                selected.runtime / "controlled_emergency_events.json",
                default=[],
            ),
        }

    context["llm_runtime"] = {}
    if selected.llm_runtime:
        context["llm_runtime"] = {
            "summary": load_json(
                selected.llm_runtime / "summary.json",
                default={},
            ),
            "validation": load_json(
                selected.llm_runtime / "validation_events.json",
                default=[],
            ),
            "candidates": load_json(
                selected.llm_runtime / "action_candidates.json",
                default=[],
            ),
        }
    return context


def load_comparison_csv(
    filename: str,
    *,
    index: DemoArtifactIndex | None = None,
    usecols: Iterable[str] = (),
) -> pd.DataFrame:
    if filename not in COMPARISON_CSV_FILES:
        raise ArtifactLoadError(f"Unsupported comparison file: {filename}")
    selected = index or latest_artifact_index()
    return load_csv(selected.comparison / filename, usecols=usecols)


def load_zone_telemetry(
    *,
    index: DemoArtifactIndex | None = None,
) -> pd.DataFrame:
    columns = (
        "timestamp",
        "energyplus_zone_name",
        "display_zone_name_controlled",
        "zone_role_controlled",
        "occupancy_controlled",
        "indoor_temperature_c_controlled",
        "cooling_setpoint_c_baseline",
        "cooling_setpoint_c_controlled",
        "heating_setpoint_c_controlled",
        "relative_humidity_percent_controlled",
        "comfort_method_controlled",
    )
    frame = load_comparison_csv(
        "aligned_zone_telemetry.csv",
        index=index,
        usecols=columns,
    ).copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    return frame


def load_facility_telemetry(
    *,
    index: DemoArtifactIndex | None = None,
) -> pd.DataFrame:
    columns = (
        "timestamp",
        "facility_electricity_kwh_baseline",
        "facility_electricity_kwh_controlled",
        "facility_demand_kw_baseline",
        "facility_demand_kw_controlled",
        "outdoor_temperature_c_controlled",
        "cooling_electricity_kwh_baseline",
        "cooling_electricity_kwh_controlled",
        "fan_electricity_kwh_baseline",
        "fan_electricity_kwh_controlled",
        "heating_electricity_kwh_baseline",
        "heating_electricity_kwh_controlled",
    )
    frame = load_comparison_csv(
        "aligned_facility_telemetry.csv",
        index=index,
        usecols=columns,
    ).copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    return frame


def latest_zone_snapshot(
    frame: pd.DataFrame,
    *,
    timestamp: pd.Timestamp | None = None,
) -> tuple[pd.Timestamp, pd.DataFrame]:
    if frame.empty or frame["timestamp"].dropna().empty:
        raise ArtifactLoadError("Zone telemetry contains no usable timestamps.")
    selected = timestamp or frame["timestamp"].dropna().max()
    available = frame.loc[frame["timestamp"].eq(selected)].copy()
    if available.empty:
        nearest_index = (frame["timestamp"] - selected).abs().idxmin()
        selected = frame.loc[nearest_index, "timestamp"]
        available = frame.loc[frame["timestamp"].eq(selected)].copy()
    return pd.Timestamp(selected), available


def approved_report_files(index: DemoArtifactIndex | None = None) -> list[Path]:
    selected = index or latest_artifact_index()
    comparison_names = (
        "final_summary.json",
        "executive_summary.md",
        "aligned_facility_telemetry.csv",
        "aligned_zone_telemetry.csv",
        "energy_comparison.csv",
        "demand_comparison.csv",
        "comfort_comparison.csv",
        "cost_comparison.csv",
        "carbon_comparison.csv",
        "action_summary.csv",
        "compatibility_report.json",
        "reproducibility_report.json",
        "safety_metrics.json",
        "reliability_metrics.json",
        "judge_summary.json",
        "comparison_manifest.json",
    )
    paths = [selected.comparison / name for name in comparison_names]
    paths.extend(
        [
            RESULTS_ROOT / "submission" / "phase11" / "submission_manifest.json",
            PROJECT_ROOT / "README.md",
            DOCS_ROOT / "SYSTEM_ARCHITECTURE.md",
            DOCS_ROOT / "DEMO_SCRIPT.md",
        ]
    )
    return [
        path.resolve()
        for path in paths
        if path.is_file() and is_approved_display_path(path)
    ]


__all__ = [
    "ArtifactLoadError",
    "COMPARISON_CSV_FILES",
    "CONTROLLED_ZONE",
    "DEMO_MODE_LIVE",
    "DEMO_MODE_REPLAY",
    "DemoArtifactIndex",
    "approved_report_files",
    "latest_artifact_index",
    "latest_llm_runtime_directory",
    "latest_phase7_directory",
    "latest_safety_directory",
    "latest_zone_snapshot",
    "load_comparison_csv",
    "load_csv",
    "load_approved_file_bytes",
    "load_demo_context",
    "load_facility_telemetry",
    "load_json",
    "load_zone_telemetry",
]
