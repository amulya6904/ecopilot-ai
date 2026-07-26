"""Append-only audit logging for every Phase 8 control decision."""

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any

from .settings import PHASE8_SETTINGS, Phase8Settings


class RuntimeAuditLog:
    def __init__(
        self,
        path: Path | None = None,
        settings: Phase8Settings = PHASE8_SETTINGS,
    ) -> None:
        self.path = settings.resolve(path or settings.audit_path)
        self._lock = Lock()

    def record(self, event_type: str, payload: Any) -> None:
        value = (
            payload.model_dump(mode="json")
            if hasattr(payload, "model_dump")
            else payload
        )
        event = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": value,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(event, default=str, allow_nan=False) + "\n"
                )


__all__ = ["RuntimeAuditLog"]
