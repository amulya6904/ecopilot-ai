"""Thread-safe JSON Lines audit records without response payload leakage."""

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any
import uuid

from mcp_service.serialization import to_json_safe


_SENSITIVE_KEYS = {"path", "executable", "command", "environment", "env", "payload", "data"}


def sanitize_inputs(value: Any) -> Any:
    safe = to_json_safe(value)
    if isinstance(safe, dict):
        return {
            key: ("[REDACTED]" if any(token in key.casefold() for token in _SENSITIVE_KEYS)
                  else sanitize_inputs(item))
            for key, item in safe.items()
        }
    if isinstance(safe, list):
        return [sanitize_inputs(item) for item in safe[:100]]
    return safe


class AuditLogger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.last_error: str | None = None

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex

    def write(self, record: dict[str, Any]) -> bool:
        clean = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **to_json_safe(record),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            encoded = json.dumps(clean, sort_keys=True, allow_nan=False)
            with self._lock:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(encoded + "\n")
            self.last_error = None
            return True
        except OSError as exc:
            self.last_error = f"{type(exc).__name__}: audit write failed"
            return False

    def latest(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        result = []
        for line in lines[-max(1, min(limit, 100)):]:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result


__all__ = ["AuditLogger", "sanitize_inputs"]
