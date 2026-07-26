"""Detailed Phase 7 artifacts and compact JSONL audit."""

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any

from mcp_service.serialization import to_json_safe
from llm.settings import LLMSettings


class AgentAuditWriter:
    _lock = threading.Lock()

    def __init__(self, settings: LLMSettings):
        self.settings = settings

    def write_artifacts(self, run_id: str, documents: dict[str, Any]) -> Path:
        root = (self.settings.resolve(self.settings.agent_artifact_root) / run_id).resolve()
        allowed = self.settings.resolve(self.settings.agent_artifact_root)
        if allowed not in root.parents:
            raise ValueError("Agent artifact path escaped configured root.")
        root.mkdir(parents=True, exist_ok=False)
        for name, value in documents.items():
            path = root / name
            if name.endswith(".txt"):
                path.write_text(str(value), encoding="utf-8")
            else:
                path.write_text(json.dumps(to_json_safe(value), indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
        return root

    def append_audit(self, record: dict[str, Any]) -> bool:
        path = self.settings.resolve(self.settings.agent_audit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        compact = {"timestamp": datetime.now(timezone.utc).isoformat(), **to_json_safe(record)}
        try:
            with self._lock:
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(compact, sort_keys=True, allow_nan=False) + "\n")
            return True
        except OSError:
            return False


__all__ = ["AgentAuditWriter"]
