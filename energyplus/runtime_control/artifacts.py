"""Complete, deterministic artifact bundle for a Phase 8 runtime run."""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

from .settings import PHASE8_SETTINGS, Phase8Settings


REQUIRED_ARTIFACTS = (
    "run_metadata.json",
    "actuator_inventory.json",
    "handle_registry.json",
    "telemetry.csv",
    "proposals.json",
    "action_candidates.json",
    "validation_events.json",
    "applied_actions.csv",
    "fallback_events.json",
    "runtime_errors.json",
    "response_analysis.json",
    "summary.json",
)


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def new_run_id(mode: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{mode}-{uuid.uuid4().hex[:8]}"


class Phase8Artifacts:
    def __init__(
        self,
        mode: str,
        *,
        run_id: str | None = None,
        settings: Phase8Settings = PHASE8_SETTINGS,
    ) -> None:
        self.settings = settings
        self.mode = mode
        self.run_id = run_id or new_run_id(mode)
        self.directory = settings.resolve(settings.artifact_root) / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.telemetry: list[dict[str, Any]] = []
        self.proposals: list[dict[str, Any]] = []
        self.candidates: list[dict[str, Any]] = []
        self.validations: list[dict[str, Any]] = []
        self.applied: list[dict[str, Any]] = []
        self.fallbacks: list[dict[str, Any]] = []
        self.runtime_errors: list[dict[str, Any]] = []
        self.observations: list[dict[str, Any]] = []
        source = settings.resolve(settings.source_model_path)
        runtime = settings.resolve(settings.runtime_model_path)
        self.metadata = {
            "run_id": self.run_id,
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_model": str(source),
            "runtime_model": str(runtime),
            "source_model_sha256": file_sha256(source),
            "runtime_model_sha256": file_sha256(runtime),
            "weather_file": str(settings.resolve(settings.weather_file_path)),
            "controlled_zone": settings.controlled_zone,
            "real_llm_enabled": settings.enable_real_llm,
            "final_optimization_result": False,
            "savings_result": False,
        }
        self.inventory: dict[str, Any] = {}
        self.handles: dict[str, Any] = {}

    @staticmethod
    def _dumpable(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return dict(value)

    def add(self, collection: str, value: Any) -> None:
        getattr(self, collection).append(self._dumpable(value))

    def _write_json(self, name: str, value: Any) -> None:
        (self.directory / name).write_text(
            json.dumps(value, indent=2, default=str, allow_nan=False),
            encoding="utf-8",
        )

    def _write_csv(self, name: str, rows: list[dict[str, Any]]) -> None:
        path = self.directory / name
        fields = sorted({key for row in rows for key in row})
        with path.open("w", newline="", encoding="utf-8") as stream:
            if fields:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

    def finalize(self, summary: dict[str, Any]) -> Path:
        final_summary = {
            "mode": self.mode,
            "classification": summary["classification"],
            "control_injection_verified": bool(
                summary.get("control_injection_verified")
            ),
            "observed_setpoint_change": bool(
                summary.get("observed_setpoint_change")
            ),
            "actuator_reset_verified": bool(
                summary.get("actuator_reset_verified")
            ),
            "multiple_intervals_completed": bool(
                summary.get("multiple_intervals_completed")
            ),
            "fallback_verified": bool(summary.get("fallback_verified")),
            "real_llm_used": bool(summary.get("real_llm_used")),
            "severe_count": int(summary.get("severe_count", 0)),
            "fatal_count": int(summary.get("fatal_count", 0)),
            "final_optimization_result": False,
            "savings_result": False,
            **summary,
            "artifact_directory": str(self.directory),
        }
        final_summary["final_optimization_result"] = False
        final_summary["savings_result"] = False
        self._write_json("run_metadata.json", self.metadata)
        self._write_json("actuator_inventory.json", self.inventory)
        self._write_json("handle_registry.json", self.handles)
        self._write_csv("telemetry.csv", self.telemetry)
        self._write_json("proposals.json", self.proposals)
        self._write_json("action_candidates.json", self.candidates)
        self._write_json("validation_events.json", self.validations)
        self._write_csv("applied_actions.csv", self.applied)
        self._write_json("fallback_events.json", self.fallbacks)
        self._write_json("runtime_errors.json", self.runtime_errors)
        self._write_json(
            "response_analysis.json",
            {"observations": self.observations},
        )
        self._write_json("summary.json", final_summary)
        return self.directory


__all__ = [
    "Phase8Artifacts",
    "REQUIRED_ARTIFACTS",
    "file_sha256",
    "new_run_id",
]
