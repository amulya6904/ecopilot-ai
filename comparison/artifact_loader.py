"""Manifest-first, repository-bounded Phase 5 and controlled artifact loading."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from energyplus.baseline.artifacts import ARTIFACT_FILENAMES

from .schemas import RunIdentity
from .settings import COMPARISON_SETTINGS, ComparisonSettings


class ArtifactLoadError(RuntimeError):
    """Structured error raised when an official artifact cannot be loaded."""

    def __init__(
        self, code: str, message: str, *, missing: list[str] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.missing = missing or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "missing": self.missing,
        }


@dataclass(frozen=True)
class LoadedRun:
    kind: Literal["baseline", "controlled"]
    directory: Path
    manifest: dict[str, Any]
    summary: dict[str, Any]
    facility: pd.DataFrame
    zone: pd.DataFrame
    actions: pd.DataFrame
    safety_summary: dict[str, Any]
    identity: RunIdentity


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ArtifactLoadError(
            "MISSING_ARTIFACT", f"Required artifact is missing: {path}",
            missing=[str(path)],
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactLoadError(
            "INVALID_ARTIFACT", f"Artifact is not valid JSON: {path}"
        ) from error
    if not isinstance(value, dict):
        raise ArtifactLoadError(
            "INVALID_ARTIFACT", f"Expected a JSON object: {path}"
        )
    return value


def _bounded_explicit_path(
    path: Path, settings: ComparisonSettings
) -> Path:
    candidate = Path(path).resolve()
    results_root = (Path(settings.repository_root) / "results").resolve()
    if candidate != results_root and results_root not in candidate.parents:
        raise ArtifactLoadError(
            "PATH_OUTSIDE_RESULTS",
            "Explicit artifact paths must remain inside project results.",
        )
    if "development" in {part.casefold() for part in candidate.parts}:
        raise ArtifactLoadError(
            "DEVELOPMENT_RESULT_REJECTED",
            "Development simulator artifacts cannot be promoted to Phase 10.",
        )
    return candidate.parent if candidate.is_file() else candidate


def _identity(
    *,
    kind: str,
    manifest: dict[str, Any],
    summary: dict[str, Any],
) -> RunIdentity:
    actual = manifest.get("actual_available_outputs", {})
    required = (
        "zone_temperature",
        "cooling_setpoint",
        "occupancy",
        "outdoor_temperature",
        "facility_electricity",
        "facility_demand",
    )
    return RunIdentity(
        run_id=str(summary.get("run_id") or manifest.get("run_id") or ""),
        mode=str(summary.get("mode") or kind),
        backend=str(summary.get("backend") or manifest.get("backend") or ""),
        source=str(summary.get("source") or manifest.get("source") or ""),
        classification=str(summary.get("classification") or ""),
        model_path=str(
            summary.get("model_path")
            or manifest.get("runtime_model_path")
            or manifest.get("derived_baseline_model_path")
            or ""
        ),
        base_model_hash=str(
            summary.get("base_model_hash")
            or manifest.get("base_model_hash")
            or ""
        ),
        derived_model_hash=str(
            summary.get("derived_model_hash")
            or manifest.get("runtime_model_hash")
            or manifest.get("derived_model_hash")
            or ""
        ),
        weather_path=str(
            summary.get("weather_path") or manifest.get("weather_path") or ""
        ),
        weather_hash=str(
            summary.get("weather_hash") or manifest.get("weather_hash") or ""
        ),
        energyplus_version=str(
            summary.get("energyplus_version")
            or summary.get("EnergyPlus_version")
            or manifest.get("energyplus_version")
            or ""
        ),
        run_period=list(manifest.get("run_period") or []),
        reporting_frequency=str(
            summary.get("reporting_frequency")
            or manifest.get("reporting_frequency")
            or ""
        ),
        interval_count=int(
            summary.get("reporting_interval_count")
            or manifest.get("interval_count")
            or 0
        ),
        zone_mapping_hash=str(
            manifest.get("zone_mapping_hash")
            or stable_json_hash(manifest.get("zone_display_mapping", {}))
        ),
        occupancy_configuration_hash=str(
            manifest.get("occupancy_configuration_hash")
            or stable_json_hash(
                manifest.get("occupancy_schedule_inventory", [])
            )
        ),
        internal_load_configuration_hash=(
            str(manifest["internal_load_configuration_hash"])
            if manifest.get("internal_load_configuration_hash")
            else stable_json_hash(
                manifest.get("internal_load_schedule_inventory", {})
            )
            if manifest.get("internal_load_schedule_inventory") is not None
            else None
        ),
        control_policy=str(
            manifest.get("control_policy")
            or ("fixed_schedule" if kind == "baseline" else "")
        ),
        severe_count=int(summary.get("severe_count", 0)),
        fatal_count=int(summary.get("fatal_count", 0)),
        success=bool(summary.get("success")),
        critical_telemetry_complete=all(bool(actual.get(key)) for key in required),
        control_injection_verified=bool(
            summary.get("control_injection_verified")
        ),
        safety_supervisor_enabled=bool(
            summary.get("safety_supervisor_enabled")
        ),
    )


def load_baseline_artifact(
    explicit_path: Path | None = None,
    *,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> LoadedRun:
    directory = (
        _bounded_explicit_path(explicit_path, settings)
        if explicit_path is not None
        else (Path(settings.repository_root) / "results" / "official").resolve()
    )
    required = {
        key: directory / filename
        for key, filename in ARTIFACT_FILENAMES.items()
        if key in {"manifest", "summary", "facility_telemetry", "zone_telemetry"}
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise ArtifactLoadError(
            "MISSING_BASELINE_ARTIFACTS",
            "The official Phase 5 baseline artifact is incomplete.",
            missing=missing,
        )
    manifest = _load_json(required["manifest"])
    summary = _load_json(required["summary"])
    if (
        summary.get("classification") != "official_energyplus_baseline"
        or summary.get("backend") != "energyplus"
        or summary.get("source") != "EnergyPlus"
        or summary.get("official_result") is not True
        or summary.get("baseline_result") is not True
        or summary.get("success") is not True
    ):
        raise ArtifactLoadError(
            "INVALID_BASELINE_CLASSIFICATION",
            "Selected baseline is not a successful official EnergyPlus baseline.",
        )
    facility = pd.read_csv(required["facility_telemetry"])
    zone = pd.read_csv(required["zone_telemetry"])
    identity = _identity(kind="baseline", manifest=manifest, summary=summary)
    return LoadedRun(
        kind="baseline",
        directory=directory,
        manifest=manifest,
        summary=summary,
        facility=facility,
        zone=zone,
        actions=pd.DataFrame(),
        safety_summary={},
        identity=identity,
    )


def _latest_controlled_directory(settings: ComparisonSettings) -> Path:
    root = settings.resolve(settings.controlled_artifact_root)
    candidates: list[Path] = []
    for directory in root.iterdir() if root.is_dir() else ():
        if not directory.is_dir():
            continue
        manifest_path = directory / "controlled_manifest.json"
        summary_path = directory / "controlled_summary.json"
        if not manifest_path.is_file() or not summary_path.is_file():
            continue
        try:
            summary = _load_json(summary_path)
        except ArtifactLoadError:
            continue
        if (
            summary.get("success") is True
            and summary.get("classification")
            == "official_energyplus_safety_supervised_controlled_evaluation"
        ):
            candidates.append(directory)
    if not candidates:
        raise ArtifactLoadError(
            "CONTROLLED_ARTIFACT_NOT_FOUND",
            "No complete official Phase 10 controlled EnergyPlus artifact exists.",
        )
    return max(candidates, key=lambda item: item.stat().st_mtime)


def load_controlled_artifact(
    explicit_path: Path | None = None,
    *,
    settings: ComparisonSettings = COMPARISON_SETTINGS,
) -> LoadedRun:
    directory = (
        _bounded_explicit_path(explicit_path, settings)
        if explicit_path is not None
        else _latest_controlled_directory(settings)
    )
    manifest_path = directory / "controlled_manifest.json"
    summary_path = directory / "controlled_summary.json"
    if not manifest_path.is_file() or not summary_path.is_file():
        raise ArtifactLoadError(
            "MISSING_CONTROLLED_MANIFEST",
            "Selected directory is not a Phase 10 controlled artifact.",
            missing=[str(manifest_path), str(summary_path)],
        )
    manifest = _load_json(manifest_path)
    summary = _load_json(summary_path)
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ArtifactLoadError(
            "INVALID_CONTROLLED_MANIFEST",
            "Controlled manifest does not declare its artifact files.",
        )
    required_names = ("facility_telemetry", "zone_telemetry", "actions")
    required = {
        name: directory / str(files.get(name, ""))
        for name in required_names
    }
    missing = [
        str(path)
        for name, path in required.items()
        if not files.get(name) or not path.is_file()
    ]
    if missing:
        raise ArtifactLoadError(
            "MISSING_CONTROLLED_ARTIFACTS",
            "The controlled EnergyPlus artifact is incomplete.",
            missing=missing,
        )
    if (
        summary.get("classification")
        != "official_energyplus_safety_supervised_controlled_evaluation"
        or summary.get("backend") != "energyplus"
        or summary.get("source") != "EnergyPlus"
        or summary.get("success") is not True
    ):
        raise ArtifactLoadError(
            "INVALID_CONTROLLED_CLASSIFICATION",
            "Selected run is not an accepted official controlled EnergyPlus run.",
        )
    if summary.get("development_result") is True:
        raise ArtifactLoadError(
            "DEVELOPMENT_RESULT_REJECTED",
            "Development artifacts cannot be used for official savings.",
        )
    safety_summary_path = directory / str(files.get("safety_summary", ""))
    safety_summary = (
        _load_json(safety_summary_path)
        if files.get("safety_summary") and safety_summary_path.is_file()
        else {}
    )
    identity = _identity(kind="controlled", manifest=manifest, summary=summary)
    return LoadedRun(
        kind="controlled",
        directory=directory,
        manifest=manifest,
        summary=summary,
        facility=pd.read_csv(required["facility_telemetry"]),
        zone=pd.read_csv(required["zone_telemetry"]),
        actions=pd.read_csv(required["actions"]),
        safety_summary=safety_summary,
        identity=identity,
    )


__all__ = [
    "ArtifactLoadError",
    "LoadedRun",
    "load_baseline_artifact",
    "load_controlled_artifact",
    "stable_json_hash",
]
