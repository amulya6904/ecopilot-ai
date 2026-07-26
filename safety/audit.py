"""Append-only, repository-bounded Phase 9 safety event audit."""

from datetime import datetime, timezone
import json
from threading import Lock
from typing import Any
import uuid

from .settings import SAFETY_SETTINGS, SafetySettings


class SafetyAuditLog:
    def __init__(
        self,
        settings: SafetySettings = SAFETY_SETTINGS,
        *,
        enabled: bool = True,
    ) -> None:
        self.path = settings.resolve(settings.audit_path)
        self.enabled = enabled
        self._lock = Lock()

    @staticmethod
    def _dumpable(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value

    def record(
        self,
        event_type: str,
        *,
        run_id: str,
        simulation_timestamp,
        action_id: str | None = None,
        state_summary: Any = None,
        rules_evaluated: Any = None,
        decision: str | None = None,
        requested_value: float | None = None,
        approved_value: float | None = None,
        safety_level: str | None = None,
        fallback_or_rollback: bool = False,
        duration_ms: float = 0.0,
        result: Any = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": f"safety-event-{uuid.uuid4().hex}",
            "event_type": event_type,
            "run_id": run_id,
            "simulation_timestamp": (
                simulation_timestamp.isoformat()
                if hasattr(simulation_timestamp, "isoformat")
                else str(simulation_timestamp)
            ),
            "wall_clock_timestamp": datetime.now(timezone.utc).isoformat(),
            "action_id": action_id,
            "state_summary": self._dumpable(state_summary),
            "rules_evaluated": self._dumpable(rules_evaluated),
            "decision": decision,
            "requested_value": requested_value,
            "approved_value": approved_value,
            "safety_level": safety_level,
            "fallback_or_rollback": fallback_or_rollback,
            "duration_ms": duration_ms,
            "result": self._dumpable(result),
        }
        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, allow_nan=False, default=str)
            with self._lock:
                with self.path.open("a", encoding="utf-8") as stream:
                    stream.write(line + "\n")
        return event


__all__ = ["SafetyAuditLog"]
