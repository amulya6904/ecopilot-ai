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


def _readvars_executable(
    installation_dir: Path | None,
    energyplus_executable: Path,
) -> Path | None:
    """Locate the ReadVarsESO companion shipped with EnergyPlus."""
    roots = [
        root
        for root in (installation_dir, energyplus_executable.parent)
        if root is not None
    ]
    candidates = [
        root / directory / name
        for root in roots
        for directory in ("PostProcess", "")
        for name in ("ReadVarsESO.exe", "ReadVarsESO")
    ]
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def _decode_timeout_output(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value or ""


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
    command.append(str(Path(settings.base_model_path).resolve()))
    started = time.monotonic()
    exit_code: int | None = None
    energyplus_timed_out = False
    readvars_timed_out = False
    readvars_exit_code: int | None = None
    readvars_failure: str | None = None
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
        energyplus_timed_out = True
        stdout = _decode_timeout_output(error.stdout)
        stderr = _decode_timeout_output(error.stderr)
    error_path = output_dir / "eplusout.err"
    eso_path = output_dir / "eplusout.eso"
    csv_path = output_dir / "eplusout.csv"
    sql_path = output_dir / "eplusout.sql"
    readvars_path: Path | None = None
    readvars_command: list[str] | None = None
    if (
        settings.readvars
        and not energyplus_timed_out
        and exit_code == 0
        and eso_path.is_file()
    ):
        readvars_path = _readvars_executable(
            status.installation_dir,
            status.executable_path,
        )
        if readvars_path is None:
            readvars_failure = "ReadVarsESO executable was not found."
        else:
            rvi_path = output_dir / "eplusout.rvi"
            rvi_path.write_text(
                f"{eso_path.resolve()}\n{csv_path.resolve()}\n",
                encoding="utf-8",
            )
            readvars_command = [str(readvars_path), str(rvi_path), "unlimited"]
            remaining_timeout = max(
                1.0,
                settings.process_timeout_seconds - (time.monotonic() - started),
            )
            try:
                readvars_process = subprocess.run(
                    readvars_command,
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    timeout=remaining_timeout,
                    check=False,
                    shell=False,
                )
                readvars_exit_code = readvars_process.returncode
                stdout += (
                    "\n\n--- ReadVarsESO ---\n" + readvars_process.stdout
                )
                stderr += (
                    "\n\n--- ReadVarsESO ---\n" + readvars_process.stderr
                )
                if readvars_exit_code != 0:
                    readvars_failure = (
                        f"ReadVarsESO exited with code {readvars_exit_code}."
                    )
            except subprocess.TimeoutExpired as error:
                readvars_timed_out = True
                stdout += (
                    "\n\n--- ReadVarsESO ---\n"
                    + _decode_timeout_output(error.stdout)
                )
                stderr += (
                    "\n\n--- ReadVarsESO ---\n"
                    + _decode_timeout_output(error.stderr)
                )
                readvars_failure = "ReadVarsESO timed out."
            except (FileNotFoundError, OSError) as error:
                readvars_failure = f"ReadVarsESO failed to start: {error}"
    duration = time.monotonic() - started
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    errors = parse_energyplus_error_file(error_path)
    telemetry_exists = csv_path.is_file() or sql_path.is_file()
    failures: list[str] = []
    if energyplus_timed_out:
        failures.append("EnergyPlus timed out.")
    elif exit_code != 0:
        failures.append(f"EnergyPlus exited with code {exit_code}.")
    if readvars_failure:
        failures.append(readvars_failure)
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
        timed_out=energyplus_timed_out or readvars_timed_out,
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
            "readvars_executable": str(readvars_path) if readvars_path else None,
            "readvars_command": readvars_command,
            "readvars_exit_code": readvars_exit_code,
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
