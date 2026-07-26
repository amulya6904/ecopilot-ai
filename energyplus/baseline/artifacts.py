"""Atomic official artifact writers for successful Phase 5 runs."""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
import math
from pathlib import Path
import tempfile
from typing import Any

import pandas as pd


ARTIFACT_FILENAMES = {
    "zone_telemetry": "phase5_energyplus_baseline_zone_telemetry.csv",
    "facility_telemetry": "phase5_energyplus_baseline_facility_telemetry.csv",
    "zone_summary": "phase5_energyplus_baseline_zone_summary.csv",
    "summary": "phase5_energyplus_baseline_summary.json",
    "errors": "phase5_energyplus_baseline_errors.json",
    "metadata": "phase5_energyplus_baseline_metadata.json",
    "manifest": "phase5_energyplus_baseline_manifest.json",
    "reproducibility": "phase5_energyplus_baseline_reproducibility.json",
}


def json_safe(value: Any) -> Any:
    """Convert pandas, pathlib, dataclass, and non-finite values to strict JSON."""
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_text(
        path,
        json.dumps(json_safe(value), indent=2, allow_nan=False) + "\n",
    )


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    _atomic_text(path, frame.to_csv(index=False))


def write_baseline_artifacts(
    *,
    success: bool,
    results_root: Path,
    zone_telemetry: pd.DataFrame,
    facility_telemetry: pd.DataFrame,
    zone_summary: pd.DataFrame,
    summary: dict[str, Any],
    errors: dict[str, Any],
    metadata: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Path]:
    """Write stable official files only after all success checks pass."""
    if not success:
        return {}
    if (
        summary.get("classification") != "official_energyplus_baseline"
        or summary.get("official_result") is not True
        or summary.get("baseline_result") is not True
        or any(
            summary.get(flag) is not False
            for flag in (
                "ai_controlled",
                "closed_loop",
                "optimized",
                "savings_result",
            )
        )
    ):
        raise ValueError("Official baseline classification flags are invalid.")
    root = Path(results_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        key: root / filename
        for key, filename in ARTIFACT_FILENAMES.items()
        if key != "reproducibility"
    }
    _atomic_csv(paths["zone_telemetry"], zone_telemetry)
    _atomic_csv(paths["facility_telemetry"], facility_telemetry)
    _atomic_csv(paths["zone_summary"], zone_summary)
    _atomic_json(paths["summary"], summary)
    _atomic_json(paths["errors"], errors)
    _atomic_json(paths["metadata"], metadata)
    _atomic_json(paths["manifest"], manifest)
    return paths


def write_reproducibility_report(
    results_root: Path, report: Any
) -> Path:
    """Atomically save the optional two-run reproducibility proof."""
    path = Path(results_root) / ARTIFACT_FILENAMES["reproducibility"]
    _atomic_json(path, report)
    return path


__all__ = [
    "ARTIFACT_FILENAMES",
    "json_safe",
    "write_baseline_artifacts",
    "write_reproducibility_report",
]
