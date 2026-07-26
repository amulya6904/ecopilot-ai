"""Safely derive the frozen Phase 5 IDF from the verified Phase 4 model."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile
from typing import Any

from energyplus.baseline.manifest import calculate_sha256
from energyplus.baseline.schedule_inspector import (
    BaselineModelInspection,
    IDFObject,
    inspect_baseline_model,
    parse_idf_objects,
)
from energyplus.baseline.settings import EnergyPlusBaselineSettings


COOLING_SCHEDULE_NAME = "ECOPILOT_BASELINE_COOLING_SCHEDULE"
HEATING_SCHEDULE_NAME = "ECOPILOT_BASELINE_HEATING_SCHEDULE"

PHASE5_HEADER = """\
!- EcoPilot AI Phase 5 Official EnergyPlus Baseline
!- Source model preserved unchanged
!- Conventional fixed-schedule HVAC policy
!- AI controlled: No
!- Closed loop: No
!- Optimized: No

"""

BASELINE_OUTPUT_VARIABLES = (
    ("*", "Zone Mean Air Temperature"),
    ("*", "Zone Thermostat Cooling Setpoint Temperature"),
    ("*", "Zone Thermostat Heating Setpoint Temperature"),
    ("*", "Zone People Occupant Count"),
    ("*", "Zone Air Relative Humidity"),
    ("*", "Zone Thermal Comfort Fanger Model PMV"),
    ("*", "Zone Thermal Comfort Fanger Model PPD"),
    ("Environment", "Site Outdoor Air Drybulb Temperature"),
    ("Environment", "Site Outdoor Air Relative Humidity"),
    ("Whole Building", "Facility Total Electricity Demand Rate"),
)

BASELINE_OUTPUT_METERS = (
    "Electricity:Facility",
    "Electricity:HVAC",
    "Cooling:Electricity",
    "Heating:Electricity",
    "Fans:Electricity",
)


@dataclass(frozen=True)
class BaselineModelBuildResult:
    success: bool
    source_model_path: Path
    destination_model_path: Path
    source_model_hash: str | None
    destination_model_hash: str | None
    schedules_inspected: int
    schedules_modified: tuple[str, ...]
    output_requests_added: tuple[str, ...]
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]
    failure_reason: str | None
    inspection_metadata_path: Path | None = None
    inspection: BaselineModelInspection | None = None


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _render_object(object_type: str, fields: list[str]) -> str:
    lines = [f"\n  {object_type},"]
    for index, value in enumerate(fields):
        suffix = ";" if index == len(fields) - 1 else ","
        lines.append(f"    {value}{suffix}")
    return "\n".join(lines)


def _replace_object_spans(
    source_text: str, replacements: list[tuple[IDFObject, str]]
) -> str:
    result = source_text
    for item, replacement in sorted(
        replacements, key=lambda pair: pair[0].start, reverse=True
    ):
        result = result[:item.start] + replacement + result[item.end:]
    return result


def _schedule_text(settings: EnergyPlusBaselineSettings) -> str:
    frequency = settings.reporting_frequency.title()
    return f"""

!- EcoPilot Phase 5 fixed thermostat schedules ({frequency} reporting)
Schedule:Compact,
    {COOLING_SCHEDULE_NAME},
    Temperature,
    Through: 12/31,
    For: AllDays,
    Until: {settings.occupied_start_hour:02d}:00,{settings.unoccupied_cooling_setpoint_c:g},
    Until: {settings.occupied_end_hour:02d}:00,{settings.occupied_cooling_setpoint_c:g},
    Until: 24:00,{settings.unoccupied_cooling_setpoint_c:g};

Schedule:Compact,
    {HEATING_SCHEDULE_NAME},
    Temperature,
    Through: 12/31,
    For: AllDays,
    Until: {settings.occupied_start_hour:02d}:00,{settings.unoccupied_heating_setpoint_c:g},
    Until: {settings.occupied_end_hour:02d}:00,{settings.occupied_heating_setpoint_c:g},
    Until: 24:00,{settings.unoccupied_heating_setpoint_c:g};
"""


def _request_identity(item: IDFObject) -> tuple[str, ...] | None:
    kind = item.object_type.casefold()
    if kind == "output:variable" and len(item.fields) >= 4:
        return (
            kind,
            item.fields[1].casefold(),
            item.fields[2].casefold(),
            item.fields[3].casefold(),
        )
    if kind == "output:meter" and len(item.fields) >= 3:
        return (kind, item.fields[1].casefold(), item.fields[2].casefold())
    if kind in {"output:sqlite", "output:variabledictionary"}:
        return (kind,)
    return None


def _output_request_text(
    source_text: str, settings: EnergyPlusBaselineSettings
) -> tuple[str, tuple[str, ...]]:
    existing = {
        identity
        for item in parse_idf_objects(source_text)
        if (identity := _request_identity(item)) is not None
    }
    frequency = settings.reporting_frequency.title()
    additions: list[str] = []
    added_names: list[str] = []
    for key, variable in BASELINE_OUTPUT_VARIABLES:
        identity = (
            "output:variable",
            key.casefold(),
            variable.casefold(),
            frequency.casefold(),
        )
        wildcard_identity = (
            "output:variable",
            "*",
            variable.casefold(),
            frequency.casefold(),
        )
        if identity in existing or (
            key.casefold() != "*" and wildcard_identity in existing
        ):
            continue
        additions.append(
            f"\nOutput:Variable,\n    {key},\n    {variable},\n    {frequency};\n"
        )
        added_names.append(variable)
        existing.add(identity)
    for meter in BASELINE_OUTPUT_METERS:
        identity = ("output:meter", meter.casefold(), frequency.casefold())
        if identity in existing:
            continue
        additions.append(
            f"\nOutput:Meter,\n    {meter},\n    {frequency};\n"
        )
        added_names.append(meter)
        existing.add(identity)
    if ("output:sqlite",) not in existing:
        additions.append("\nOutput:SQLite,\n    SimpleAndTabular;\n")
        added_names.append("Output:SQLite")
    if ("output:variabledictionary",) not in existing:
        additions.append("\nOutput:VariableDictionary,\n    Regular;\n")
        added_names.append("Output:VariableDictionary")
    return "".join(additions), tuple(added_names)


def _build_metadata(
    result: BaselineModelBuildResult,
    inspection: BaselineModelInspection,
) -> dict[str, Any]:
    data = {
        key: _json_value(value)
        for key, value in asdict(result).items()
        if key != "inspection"
    }
    data["inspection"] = inspection.to_dict()
    data["cooling_schedule_name"] = COOLING_SCHEDULE_NAME
    data["heating_schedule_name"] = HEATING_SCHEDULE_NAME
    return data


def build_phase5_baseline_model(
    source_model_path: Path,
    destination_model_path: Path,
    settings: EnergyPlusBaselineSettings,
) -> BaselineModelBuildResult:
    """Create a deterministic baseline IDF while preserving Phase 4 source bytes."""
    source = Path(source_model_path).resolve()
    destination = Path(destination_model_path).resolve()
    source_hash: str | None = None
    inspection: BaselineModelInspection | None = None
    metadata_path = destination.with_suffix(".inspection.json")
    try:
        if not source.is_file():
            raise FileNotFoundError(f"Source EnergyPlus model is missing: {source}")
        source_hash = calculate_sha256(source)
        root = Path(settings.repository_root).resolve()
        models_root = (root / "energyplus" / "models").resolve()
        if destination == source:
            raise ValueError("Baseline destination must differ from the source model.")
        if destination != models_root and models_root not in destination.parents:
            raise ValueError(
                "Baseline destination must remain under energyplus/models."
            )
        inspection = inspect_baseline_model(source)
        if not inspection.thermostat_references:
            raise ValueError("No ZoneControl:Thermostat objects were found.")
        text = source.read_text(encoding="utf-8", errors="replace")
        objects = parse_idf_objects(text)
        relevant_setpoints = {
            name.casefold()
            for thermostat in inspection.thermostat_references
            for name in thermostat.setpoint_object_names
        }
        replacements: list[tuple[IDFObject, str]] = []
        modified: list[str] = []
        for item in objects:
            if item.name.casefold() not in relevant_setpoints:
                continue
            kind = item.object_type.casefold()
            fields = list(item.fields[1:])
            if kind.endswith("singleheating") and len(fields) >= 2:
                fields[1] = HEATING_SCHEDULE_NAME
            elif kind.endswith("singlecooling") and len(fields) >= 2:
                fields[1] = COOLING_SCHEDULE_NAME
            elif kind.endswith("dualsetpoint") and len(fields) >= 3:
                fields[1] = HEATING_SCHEDULE_NAME
                fields[2] = COOLING_SCHEDULE_NAME
            else:
                continue
            replacements.append(
                (item, _render_object(item.object_type, fields))
            )
            modified.append(item.name)
        if not replacements:
            raise ValueError("No referenced thermostat-setpoint objects were modified.")
        derived = _replace_object_spans(text, replacements)
        output_additions, output_added = _output_request_text(derived, settings)
        derived = (
            PHASE5_HEADER
            + derived.lstrip("\ufeff")
            + _schedule_text(settings)
            + output_additions
        )
        _atomic_write_text(destination, derived)
        if not destination.is_file() or destination.stat().st_size == 0:
            raise OSError("Derived baseline model was not written.")
        destination_hash = calculate_sha256(destination)
        if calculate_sha256(source) != source_hash:
            raise RuntimeError("Source model changed while building the baseline.")
        result = BaselineModelBuildResult(
            success=True,
            source_model_path=source,
            destination_model_path=destination,
            source_model_hash=source_hash,
            destination_model_hash=destination_hash,
            schedules_inspected=len(inspection.schedules),
            schedules_modified=tuple(modified),
            output_requests_added=output_added,
            warnings=(),
            assumptions=(
                "The verified Phase 4 example model and geometry are retained.",
                "Existing People, Lights, ElectricEquipment, HVAC availability, "
                "and ventilation schedules are preserved.",
                "The 16 C unoccupied heating setback is valid under the IDF "
                "Temperature schedule type; Phase 1 cooling-candidate limits do "
                "not define the EnergyPlus heating setback range.",
                "PLENUM-1 is not referenced by an occupied ZoneControl:Thermostat "
                "and is excluded from occupied comfort metrics.",
            ),
            failure_reason=None,
            inspection_metadata_path=metadata_path,
            inspection=inspection,
        )
        _atomic_write_text(
            metadata_path,
            json.dumps(_build_metadata(result, inspection), indent=2),
        )
        return result
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        return BaselineModelBuildResult(
            success=False,
            source_model_path=source,
            destination_model_path=destination,
            source_model_hash=source_hash,
            destination_model_hash=None,
            schedules_inspected=len(inspection.schedules) if inspection else 0,
            schedules_modified=(),
            output_requests_added=(),
            warnings=(),
            assumptions=(),
            failure_reason=str(error),
            inspection_metadata_path=None,
            inspection=inspection,
        )


__all__ = [
    "BASELINE_OUTPUT_METERS",
    "BASELINE_OUTPUT_VARIABLES",
    "BaselineModelBuildResult",
    "COOLING_SCHEDULE_NAME",
    "HEATING_SCHEDULE_NAME",
    "build_phase5_baseline_model",
]
