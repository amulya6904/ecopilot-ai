"""Official artifact readers and the single controlled execution tool."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import asdict
from pathlib import Path
import json
import subprocess
import sys
from typing import Any

from energyplus.baseline.reproducibility import compare_baseline_runs
from energyplus.baseline.runner import run_energyplus_baseline
from mcp_service.context import MCPApplicationContext
from mcp_service.errors import ErrorCode, MCPToolError
from mcp_service.tools import execute_tool


_MACHINE_PATH_KEYS = {
    "executable_path", "base_model_path", "derived_baseline_model_path",
    "model_path", "weather_path",
}


def _sanitize_manifest(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("[configured local path]" if key in _MACHINE_PATH_KEYS else _sanitize_manifest(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_manifest(item) for item in value]
    return value


def get_official_baseline_summary(context: MCPApplicationContext) -> dict[str, Any]:
    return execute_tool(
        context, "get_official_baseline_summary", {},
        lambda: context.load_json("summary.json"),
    )


def get_baseline_manifest(context: MCPApplicationContext) -> dict[str, Any]:
    return execute_tool(
        context, "get_baseline_manifest", {},
        lambda: _sanitize_manifest(context.load_json("manifest.json")),
    )


def get_latest_energyplus_run(context: MCPApplicationContext) -> dict[str, Any]:
    def handler() -> Any:
        candidates: list[tuple[float, str, Path]] = []
        for path in (
            context.artifact_path("summary.json"),
            *context.settings.resolve(Path("energyplus/metadata")).glob("*.json"),
        ):
            if path.is_file():
                candidates.append((path.stat().st_mtime, "baseline" if "baseline_summary" in path.name else "simulation", path))
        if not candidates:
            raise MCPToolError(ErrorCode.ARTIFACT_NOT_FOUND, "No official EnergyPlus run metadata is available.")
        _, kind, path = max(candidates, key=lambda item: item[0])
        if kind == "baseline":
            raw = context.load_json("summary.json")
        else:
            import json
            raw = json.loads(path.read_text(encoding="utf-8"))
        keys = (
            "run_id", "success", "source", "backend", "classification",
            "official_result", "baseline_result", "warning_count", "severe_count",
            "fatal_count", "duration_seconds",
        )
        return {"run_type": kind, **{key: raw.get(key) for key in keys}}
    return execute_tool(context, "get_latest_energyplus_run", {}, handler)


def run_official_baseline(
    context: MCPApplicationContext,
    *,
    verify_reproducibility: bool = False,
    force_rebuild: bool = False,
) -> dict[str, Any]:
    inputs = {
        "verify_reproducibility": verify_reproducibility,
        "force_rebuild": force_rebuild,
    }

    def handler() -> Any:
        if not context.settings.baseline_run_tool_enabled:
            raise MCPToolError(ErrorCode.INVALID_REQUEST, "Baseline execution is disabled.")
        if not context.execution_lock.acquire(blocking=False):
            raise MCPToolError(ErrorCode.RUN_ALREADY_IN_PROGRESS, "An official baseline run is already in progress.")
        if context.baseline_runner is run_energyplus_baseline:
            try:
                command = [
                    sys.executable, "-m", "scripts.run_phase6_baseline_worker",
                ]
                if verify_reproducibility:
                    command.append("--verify-reproducibility")
                if force_rebuild:
                    command.append("--force-rebuild")
                try:
                    completed = subprocess.run(
                        command,
                        cwd=context.settings.repository_root,
                        capture_output=True,
                        text=True,
                        timeout=context.settings.tool_timeout_seconds,
                        check=False,
                        shell=False,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise MCPToolError(
                        ErrorCode.TOOL_TIMEOUT,
                        "Official baseline run exceeded the configured timeout.",
                    ) from exc
                try:
                    result = json.loads(completed.stdout)
                except json.JSONDecodeError as exc:
                    raise MCPToolError(
                        ErrorCode.TOOL_EXECUTION_FAILED,
                        "The isolated official baseline worker returned no valid result.",
                    ) from exc
                if completed.returncode != 0 or result.get("success") is not True:
                    raise MCPToolError(
                        ErrorCode.TOOL_EXECUTION_FAILED,
                        str(result.get("failure_reason") or "Official baseline execution failed."),
                    )
                result.pop("success", None)
                return result
            finally:
                context.execution_lock.release()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ecopilot-baseline")
        try:
            first_future = executor.submit(
                context.baseline_runner,
                context.baseline_settings,
                rebuild_model=force_rebuild,
            )
            try:
                first = first_future.result(timeout=context.settings.tool_timeout_seconds)
            except FutureTimeout as exc:
                first_future.cancel()
                raise MCPToolError(ErrorCode.TOOL_TIMEOUT, "Official baseline run exceeded the configured timeout.") from exc
            if not first.success:
                raise MCPToolError(
                    ErrorCode.TOOL_EXECUTION_FAILED,
                    first.failure_reason or "Official baseline execution failed.",
                )
            reproducibility = None
            if verify_reproducibility:
                second_future = executor.submit(
                    context.baseline_runner,
                    context.baseline_settings,
                    rebuild_model=True,
                )
                try:
                    second = second_future.result(timeout=context.settings.tool_timeout_seconds)
                except FutureTimeout as exc:
                    second_future.cancel()
                    raise MCPToolError(ErrorCode.TOOL_TIMEOUT, "Reproducibility run exceeded the configured timeout.") from exc
                if not second.success:
                    raise MCPToolError(ErrorCode.TOOL_EXECUTION_FAILED, second.failure_reason or "Reproducibility run failed.")
                reproducibility = asdict(compare_baseline_runs(
                    first, second, context.baseline_settings.reproducibility_tolerance
                ))
            summary_keys = (
                "run_id", "classification", "official_result", "baseline_result",
                "total_facility_electricity_kwh", "peak_facility_demand_kw",
                "thermostat_adherence_percent", "warning_count", "severe_count",
                "fatal_count",
            )
            return {
                "summary": {key: first.baseline_summary.get(key) for key in summary_keys},
                "artifacts": {
                    key: str(path.relative_to(context.settings.repository_root))
                    if context.settings.repository_root in path.resolve().parents else path.name
                    for key, path in first.artifact_paths.items()
                },
                "reproducibility": reproducibility,
                "control_modification": False,
                "lightweight_fallback": False,
            }
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            context.execution_lock.release()

    return execute_tool(context, "run_official_baseline", inputs, handler)


__all__ = [
    "get_baseline_manifest", "get_latest_energyplus_run",
    "get_official_baseline_summary", "run_official_baseline",
]
