"""Frozen, environment-configurable local Ollama agent settings."""

from dataclasses import dataclass, field
import os
from pathlib import Path


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


@dataclass(frozen=True)
class LLMSettings:
    provider: str = "ollama"
    host: str = field(default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    model: str = field(default_factory=lambda: os.environ.get("ECOPILOT_LLM_MODEL", "qwen3:4b"))
    temperature: float = field(default_factory=lambda: _float("ECOPILOT_LLM_TEMPERATURE", 0.1))
    think: bool = field(default_factory=lambda: _bool("ECOPILOT_LLM_THINK", False))
    request_timeout_seconds: int = field(default_factory=lambda: _int("ECOPILOT_LLM_TIMEOUT_SECONDS", 180))
    final_request_timeout_seconds: int = field(default_factory=lambda: _int("ECOPILOT_LLM_FINAL_TIMEOUT_SECONDS", 180))
    agent_run_timeout_seconds: int = field(default_factory=lambda: _int("ECOPILOT_AGENT_RUN_TIMEOUT_SECONDS", 360))
    max_tool_rounds: int = field(default_factory=lambda: _int("ECOPILOT_AGENT_MAX_TOOL_ROUNDS", 4))
    max_retries: int = field(default_factory=lambda: _int("ECOPILOT_AGENT_MAX_RETRIES", 1))
    num_predict: int = field(default_factory=lambda: _int("ECOPILOT_LLM_NUM_PREDICT", 192))
    num_ctx: int = field(default_factory=lambda: _int("ECOPILOT_LLM_NUM_CTX", 4_096))
    max_tool_result_characters: int = 20_000
    max_context_characters: int = 50_000
    advisory_only: bool = True
    control_execution_enabled: bool = False
    structured_output_required: bool = True
    minimum_deadband_c: float = 1.0
    repository_root: Path = field(default_factory=lambda: Path(__file__).parents[1])
    agent_artifact_root: Path = Path("results/agent/phase7")
    agent_audit_path: Path = Path("results/audit/agent_runs.jsonl")

    def __post_init__(self) -> None:
        if self.provider != "ollama":
            raise ValueError("Phase 7 supports only the local Ollama provider.")
        if not self.host.startswith(("http://127.0.0.1", "http://localhost")):
            raise ValueError("Phase 7 Ollama host must remain local.")
        if not self.model.strip():
            raise ValueError("Configured model cannot be empty.")
        if not 0 <= self.temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1.")
        if (
            self.request_timeout_seconds <= 0
            or self.final_request_timeout_seconds <= 0
            or self.agent_run_timeout_seconds <= 0
            or self.max_tool_rounds <= 0
            or self.num_predict <= 0
            or self.num_ctx <= 0
        ):
            raise ValueError(
                "Request timeouts, agent timeout, tool rounds, and generation limits "
                "must be positive."
            )
        if self.max_retries < 0:
            raise ValueError("Maximum retries cannot be negative.")
        if min(self.max_tool_result_characters, self.max_context_characters) <= 0:
            raise ValueError("Context limits must be positive.")
        if not self.advisory_only or self.control_execution_enabled:
            raise ValueError("Phase 7 must remain advisory-only with execution disabled.")
        root = Path(self.repository_root).resolve()
        for label, path in (
            ("Agent artifact", self.agent_artifact_root),
            ("Agent audit", self.agent_audit_path),
        ):
            resolved = self.resolve(path)
            if resolved != root and root not in resolved.parents:
                raise ValueError(f"{label} path must remain inside the repository.")

    def resolve(self, path: Path) -> Path:
        candidate = Path(path)
        return candidate.resolve() if candidate.is_absolute() else (Path(self.repository_root).resolve() / candidate).resolve()


LLM_SETTINGS = LLMSettings()

__all__ = ["LLM_SETTINGS", "LLMSettings"]
