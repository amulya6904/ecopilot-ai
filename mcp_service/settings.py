"""Frozen Phase 6 MCP settings and repository-path validation."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MCPSettings:
    server_name: str = "ecopilot-energyplus"
    server_version: str = "6.0.0"
    mcp_sdk_version: str = "1.28.1"
    protocol_transport: str = "stdio"
    read_only_default: bool = True
    baseline_run_tool_enabled: bool = True
    control_tools_enabled: bool = False
    max_telemetry_records: int = 500
    default_telemetry_records: int = 200
    max_error_records: int = 100
    max_raw_log_characters: int = 10_000
    max_response_bytes: int = 1_000_000
    tool_timeout_seconds: int = 300
    repository_root: Path = field(default_factory=lambda: Path(__file__).parents[1])
    audit_log_path: Path = Path("results/audit/mcp_tool_calls.jsonl")
    official_results_root: Path = Path("results/official")
    allowed_aggregations: tuple[str, ...] = ("raw", "hourly", "daily")

    def __post_init__(self) -> None:
        positive = (
            self.max_telemetry_records,
            self.default_telemetry_records,
            self.max_error_records,
            self.max_raw_log_characters,
            self.max_response_bytes,
            self.tool_timeout_seconds,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("All MCP limits and timeouts must be positive.")
        if self.default_telemetry_records > self.max_telemetry_records:
            raise ValueError("Default telemetry limit cannot exceed the maximum.")
        if self.control_tools_enabled:
            raise ValueError("Control tools must remain disabled in Phase 6.")
        if self.protocol_transport != "stdio":
            raise ValueError("Phase 6 supports only the local stdio transport.")
        if not self.allowed_aggregations or any(
            value not in {"raw", "hourly", "daily"}
            for value in self.allowed_aggregations
        ):
            raise ValueError("MCP aggregations must use the Phase 6 allowlist.")
        root = Path(self.repository_root).resolve()
        for label, configured in (
            ("Audit", self.audit_log_path),
            ("Official results", self.official_results_root),
        ):
            resolved = self.resolve(configured)
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"{label} path must remain inside the repository.")

    def resolve(self, path: Path) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate.resolve()
        return (Path(self.repository_root).resolve() / candidate).resolve()


MCP_SETTINGS = MCPSettings()

__all__ = ["MCP_SETTINGS", "MCPSettings"]
