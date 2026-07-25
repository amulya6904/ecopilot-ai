"""Minimal isolated EnergyPlus batch runner for Phase 4 validation."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
import uuid

from config.settings import ENERGYPLUS, EnergyPlusSettings
from energyplus.adapter.discovery import discover_energyplus
from energyplus.adapter.error_parser import (
    classify_energyplus_warning,
    parse_energyplus_error_file,
)


@dataclass(frozen=True)
class EnergyPlusRunResult:
    run_id: str
    success: bool
    exit_code: int | None
    timed_out: bool
    duration_seconds: float
    output_dir: Path
    error_file_path: Path | None
    eso_output_path: Path | None
    csv_output_path: Path | None
    sql_output_path: Path | None
    stdout_log_path: Path
    stderr_log_path: Path
    metadata_path: Path
    warning_count: int
    severe_count: int
    fatal_count: int
    failure_reason: str | None
    backend: str = "energyplus"
    source: str = "EnergyPlus"
    classification: str = "official_energyplus_simulation"
    official_result: bool = False
    ai_controlled: bool = False
    closed_loop: bool = False
    optimized: bool = False
    savings_result: bool = False


def _json_value(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def run_energyplus(
    settings: EnergyPlusSettings | None = None,
    *,
    run_id: str | None = None,
) -> EnergyPlusRunResult:
    """Execute the explicitly configured EnergyPlus backend without fallback."""
    settings = settings or ENERGYPLUS
    status = discover_energyplus(settings)
    if not status.ready_for_run or status.executable_path is None:
        raise RuntimeError(
            "EnergyPlus is not ready: " + "; ".join(status.readiness_issues)
        )
    identifier = run_id or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    output_root = Path(settings.output_root).resolve()
    output_dir = output_root / identifier
    output_dir.mkdir(parents=True, exist_ok=False)
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    command = [
        str(status.executable_path),
        "--weather",
        str(Path(settings.weather_file_path).resolve()),
        "--output-directory",
        str(output_dir),
    ]
    if settings.expand_objects:
        command.append("--expandobjects")
    if settings.readvars:
        command.append("--readvars")
    command.append(str(Path(settings.base_model_path).resolve()))
    started = time.monotonic()
    exit_code: int | None = None
    timed_out = False
    stdout = ""
    stderr = ""
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.process_timeout_seconds,
            check=False,
            shell=False,
        )
        exit_code = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
    duration = time.monotonic() - started
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    error_path = output_dir / "eplusout.err"
    eso_path = output_dir / "eplusout.eso"
    csv_path = output_dir / "eplusout.csv"
    sql_path = output_dir / "eplusout.sql"
    errors = parse_energyplus_error_file(error_path)
    telemetry_exists = csv_path.is_file() or sql_path.is_file()
    failures: list[str] = []
    if timed_out:
        failures.append("EnergyPlus timed out.")
    elif exit_code != 0:
        failures.append(f"EnergyPlus exited with code {exit_code}.")
    if not error_path.is_file():
        failures.append("eplusout.err is missing.")
    if errors.severe_count:
        failures.append(f"{errors.severe_count} severe error(s) reported.")
    if errors.fatal_count:
        failures.append(f"{errors.fatal_count} fatal error(s) reported.")
    if not eso_path.is_file():
        failures.append("eplusout.eso is missing.")
    if not telemetry_exists:
        failures.append("No CSV or SQL telemetry output was produced.")
    success = not failures
    metadata_root = Path(settings.metadata_root)
    metadata_root.mkdir(parents=True, exist_ok=True)
    metadata_path = metadata_root / f"{identifier}.json"
    result = EnergyPlusRunResult(
        run_id=identifier,
        success=success,
        exit_code=exit_code,
        timed_out=timed_out,
        duration_seconds=duration,
        output_dir=output_dir,
        error_file_path=error_path if error_path.is_file() else None,
        eso_output_path=eso_path if eso_path.is_file() else None,
        csv_output_path=csv_path if csv_path.is_file() else None,
        sql_output_path=sql_path if sql_path.is_file() else None,
        stdout_log_path=stdout_path,
        stderr_log_path=stderr_path,
        metadata_path=metadata_path,
        warning_count=errors.warning_count,
        severe_count=errors.severe_count,
        fatal_count=errors.fatal_count,
        failure_reason=" ".join(failures) or None,
        official_result=success,
    )
    metadata = {
        key: _json_value(value)
        for key, value in asdict(result).items()
    }
    metadata.update(
        {
            "detected_version": status.detected_version,
            "executable_path": str(status.executable_path),
            "model_path": str(Path(settings.base_model_path).resolve()),
            "weather_path": str(Path(settings.weather_file_path).resolve()),
            "warnings": [
                {
                    "message": record.message,
                    "classification": classify_energyplus_warning(record.message),
                    "raw_excerpt": record.raw_log_excerpt,
                }
                for record in errors.records
                if record.severity == "warning"
            ],
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return result
