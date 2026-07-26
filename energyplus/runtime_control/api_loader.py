"""Controlled lazy loading of the EnergyPlus installation-provided Python API."""

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
from pathlib import Path
import sys
from typing import Any, Iterator

from .settings import PHASE8_SETTINGS, Phase8Settings


@dataclass(frozen=True)
class EnergyPlusRuntimeAvailability:
    available: bool
    installation_root: Path
    API_version: str | None
    EnergyPlus_version: str | None
    pyenergyplus_importable: bool
    library_available: bool
    readiness_issues: tuple[str, ...]


@contextmanager
def _controlled_import_path(root: Path) -> Iterator[None]:
    text = str(root)
    added = text not in sys.path
    if added:
        sys.path.insert(0, text)
    try:
        yield
    finally:
        if added:
            try:
                sys.path.remove(text)
            except ValueError:
                pass


def _library_path(root: Path) -> Path:
    if sys.platform.startswith("win"):
        return root / "energyplusapi.dll"
    if sys.platform == "darwin":
        return root / "libenergyplusapi.dylib"
    return root / "libenergyplusapi.so"


def load_energyplus_api(
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> tuple[Any | None, EnergyPlusRuntimeAvailability]:
    """Instantiate EnergyPlusAPI without making project imports depend on it."""
    root = Path(settings.installation_root).resolve()
    issues = list(settings.validate_runtime_paths())
    library = _library_path(root)
    library_available = library.is_file()
    if not library_available:
        issues.append(f"EnergyPlus API library was not found: {library}")
    importable = False
    api_version: str | None = None
    energyplus_version: str | None = None
    api: Any | None = None
    try:
        with _controlled_import_path(root):
            module = importlib.import_module("pyenergyplus.api")
            cls = getattr(module, "EnergyPlusAPI")
            importable = True
            api_version = str(cls.api_version())
            api = cls()
        for member in ("state_manager", "runtime", "exchange"):
            if not hasattr(api, member):
                issues.append(f"EnergyPlusAPI is missing required member: {member}")
        executable = root / ("energyplus.exe" if sys.platform.startswith("win") else "energyplus")
        if executable.is_file():
            from energyplus.adapter.discovery import get_energyplus_version

            energyplus_version = get_energyplus_version(executable)
        if api is not None:
            state = api.state_manager.new_state()
            try:
                api.verify_api_version_match(state)
            finally:
                api.state_manager.delete_state(state)
    except Exception as exc:
        issues.append(
            f"EnergyPlus Python API could not be loaded: {type(exc).__name__}: {exc}"
        )
        api = None
    availability = EnergyPlusRuntimeAvailability(
        available=(
            api is not None
            and importable
            and library_available
            and not issues
        ),
        installation_root=root,
        API_version=api_version,
        EnergyPlus_version=energyplus_version,
        pyenergyplus_importable=importable,
        library_available=library_available,
        readiness_issues=tuple(dict.fromkeys(issues)),
    )
    return api, availability


def inspect_runtime_availability(
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> EnergyPlusRuntimeAvailability:
    return load_energyplus_api(settings)[1]


__all__ = [
    "EnergyPlusRuntimeAvailability",
    "inspect_runtime_availability",
    "load_energyplus_api",
]
