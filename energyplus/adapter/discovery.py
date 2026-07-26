"""Bounded EnergyPlus installation discovery and readiness validation."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess

from config.settings import ENERGYPLUS, EnergyPlusSettings


@dataclass(frozen=True)
class EnergyPlusAvailability:
    installed: bool
    available: bool
    ready_for_run: bool
    executable_found: bool
    executable_path: Path | None
    installation_dir: Path | None
    idd_path: Path | None
    idd_found: bool
    detected_version: str | None
    expected_version: str | None
    version_compatible: bool | None
    model_exists: bool
    weather_exists: bool
    output_root_ready: bool
    reason: str | None
    readiness_issues: tuple[str, ...]


def _meaningful(path: Path | str | None) -> bool:
    return path is not None and str(path).strip() not in {"", "."}


def _candidate_executables(settings: EnergyPlusSettings) -> list[Path]:
    candidates: list[Path] = []
    if _meaningful(settings.executable_path):
        candidates.append(Path(settings.executable_path))
    environment_executable = os.environ.get("ENERGYPLUS_EXECUTABLE")
    if environment_executable:
        candidates.append(Path(environment_executable))
    homes = []
    if _meaningful(settings.installation_dir):
        homes.append(Path(settings.installation_dir))
    if os.environ.get("ENERGYPLUS_HOME"):
        homes.append(Path(os.environ["ENERGYPLUS_HOME"]))
    if os.name == "nt":
        homes.extend(
            path
            for version in ("26-1-0", "25-2-0", "25-1-0", "24-2-0", "24-1-0")
            if (path := Path(f"C:/EnergyPlusV{version}")).is_dir()
        )
    for home in homes:
        candidates.extend((home / "energyplus.exe", home / "energyplus"))
    candidates.extend((Path("energyplus.exe"), Path("energyplus")))
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def get_energyplus_version(
    executable_path: Path, timeout_seconds: int = 15
) -> str | None:
    """Return a normalized EnergyPlus version or ``None`` on command failure."""
    try:
        completed = subprocess.run(
            [str(executable_path), "--version"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    match = re.search(
        r"EnergyPlus(?:,\s*Version)?\s*([0-9]+(?:[.-][0-9]+){1,2})",
        output,
        re.I,
    )
    return match.group(1).replace("-", ".") if match else (output or None)


def _resolve_idd(settings: EnergyPlusSettings, installation: Path | None) -> Path | None:
    if _meaningful(settings.idd_path) and Path(settings.idd_path).is_file():
        return Path(settings.idd_path).resolve()
    if installation is not None:
        candidate = installation / "Energy+.idd"
        if candidate.is_file():
            return candidate.resolve()
    return None


def discover_energyplus(
    settings: EnergyPlusSettings | None = None,
) -> EnergyPlusAvailability:
    """Discover the executable and validate all inputs needed for a Phase 4 run."""
    settings = settings or ENERGYPLUS
    executable = next(
        (candidate.resolve() for candidate in _candidate_executables(settings)
         if candidate.is_file()),
        None,
    )
    installation = executable.parent if executable is not None else (
        Path(settings.installation_dir).resolve()
        if _meaningful(settings.installation_dir)
        and Path(settings.installation_dir).is_dir()
        else None
    )
    detected = get_energyplus_version(executable) if executable else None
    expected = settings.expected_version
    compatible = None if not expected or not detected else detected.startswith(expected)
    model_exists = Path(settings.base_model_path).is_file()
    weather_exists = Path(settings.weather_file_path).is_file()
    output_ready = False
    try:
        Path(settings.output_root).mkdir(parents=True, exist_ok=True)
        output_ready = Path(settings.output_root).is_dir()
    except OSError:
        output_ready = False
    idd = _resolve_idd(settings, installation)
    issues: list[str] = []
    if executable is None:
        issues.append("EnergyPlus executable was not found.")
    elif detected is None:
        issues.append("EnergyPlus version could not be determined.")
    if expected and compatible is False:
        issues.append(
            f"Detected EnergyPlus {detected} is incompatible with expected {expected}."
        )
    if idd is None:
        issues.append("EnergyPlus IDD file was not found.")
    if not model_exists:
        issues.append(f"Configured IDF does not exist: {settings.base_model_path}")
    if not weather_exists:
        issues.append(f"Configured EPW does not exist: {settings.weather_file_path}")
    if not output_ready:
        issues.append(f"Output root is not writable: {settings.output_root}")
    installed = executable is not None and idd is not None
    available = not issues
    return EnergyPlusAvailability(
        installed=installed,
        available=available,
        ready_for_run=available,
        executable_found=executable is not None,
        executable_path=executable,
        installation_dir=installation,
        idd_path=idd,
        idd_found=idd is not None,
        detected_version=detected,
        expected_version=expected,
        version_compatible=compatible,
        model_exists=model_exists,
        weather_exists=weather_exists,
        output_root_ready=output_ready,
        reason=issues[0] if issues else None,
        readiness_issues=tuple(issues),
    )
