"""Dependency-injected services for MCP tools and resources."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import threading
from typing import Any, Callable

import pandas as pd

from backends import EnergyPlusBackend
from energyplus.baseline.runner import EnergyPlusBaselineRunResult, run_energyplus_baseline
from energyplus.baseline.settings import ENERGYPLUS_BASELINE, EnergyPlusBaselineSettings
from mcp_service.audit import AuditLogger
from mcp_service.errors import ErrorCode, MCPToolError
from mcp_service.settings import MCP_SETTINGS, MCPSettings


@dataclass
class MCPApplicationContext:
    settings: MCPSettings = MCP_SETTINGS
    baseline_settings: EnergyPlusBaselineSettings = ENERGYPLUS_BASELINE
    backend_factory: Callable[[], Any] = EnergyPlusBackend
    baseline_runner: Callable[..., EnergyPlusBaselineRunResult] = run_energyplus_baseline
    execution_lock: threading.Lock = field(default_factory=threading.Lock)
    audit_logger: AuditLogger | None = None

    def __post_init__(self) -> None:
        if self.audit_logger is None:
            self.audit_logger = AuditLogger(self.settings.resolve(self.settings.audit_log_path))

    @property
    def results_root(self) -> Path:
        return self.settings.resolve(self.settings.official_results_root)

    def artifact_path(self, suffix: str) -> Path:
        path = (self.results_root / f"phase5_energyplus_baseline_{suffix}").resolve()
        if path != self.results_root and self.results_root not in path.parents:
            raise MCPToolError(ErrorCode.INVALID_REQUEST, "Artifact path escaped configured root.")
        return path

    def load_json(self, suffix: str) -> dict[str, Any]:
        path = self.artifact_path(suffix)
        if not path.is_file():
            raise MCPToolError(ErrorCode.ARTIFACT_NOT_FOUND, f"Official artifact is unavailable: {path.name}.")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MCPToolError(ErrorCode.BASELINE_NOT_AVAILABLE, f"Official artifact is unreadable: {path.name}.") from exc
        if not isinstance(value, dict):
            raise MCPToolError(ErrorCode.BASELINE_NOT_AVAILABLE, f"Official artifact is invalid: {path.name}.")
        return value

    def load_csv(self, suffix: str) -> pd.DataFrame:
        path = self.artifact_path(suffix)
        if not path.is_file():
            raise MCPToolError(ErrorCode.ARTIFACT_NOT_FOUND, f"Official artifact is unavailable: {path.name}.")
        try:
            return pd.read_csv(path)
        except (OSError, pd.errors.ParserError) as exc:
            raise MCPToolError(ErrorCode.BASELINE_NOT_AVAILABLE, f"Official telemetry is unreadable: {path.name}.") from exc


def create_application_context(settings: MCPSettings | None = None) -> MCPApplicationContext:
    return MCPApplicationContext(settings=settings or MCP_SETTINGS)


__all__ = ["MCPApplicationContext", "create_application_context"]
