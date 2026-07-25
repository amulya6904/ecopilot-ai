"""Object-level inspection of schedules, loads, and thermostats in an IDF."""

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterable


@dataclass(frozen=True)
class IDFObject:
    """A parsed IDF object with its exact source span."""

    object_type: str
    fields: tuple[str, ...]
    raw_text: str
    start: int
    end: int

    @property
    def name(self) -> str:
        return self.fields[1] if len(self.fields) > 1 else ""


@dataclass(frozen=True)
class ScheduleReference:
    object_type: str
    object_name: str
    referenced_schedule: str | None
    referenced_zones: tuple[str, ...]
    probable_purpose: str
    modification_strategy: str
    assumption_note: str


@dataclass(frozen=True)
class ThermostatReference:
    object_type: str
    object_name: str
    referenced_schedule: str | None
    referenced_zones: tuple[str, ...]
    probable_purpose: str
    modification_strategy: str
    assumption_note: str
    heating_schedule_name: str | None = None
    cooling_schedule_name: str | None = None
    setpoint_object_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class OccupancyReference:
    object_type: str
    object_name: str
    referenced_schedule: str | None
    referenced_zones: tuple[str, ...]
    probable_purpose: str
    modification_strategy: str
    assumption_note: str
    design_people: float | None = None


@dataclass(frozen=True)
class BaselineModelInspection:
    model_path: Path
    schedules: tuple[ScheduleReference, ...]
    thermostat_references: tuple[ThermostatReference, ...]
    occupancy_references: tuple[OccupancyReference, ...]
    people_objects: tuple[ScheduleReference, ...]
    lights_objects: tuple[ScheduleReference, ...]
    electric_equipment_objects: tuple[ScheduleReference, ...]
    hvac_availability_schedules: tuple[ScheduleReference, ...]
    output_requests: tuple[ScheduleReference, ...]
    run_periods: tuple[tuple[str, ...], ...]
    timesteps: tuple[tuple[str, ...], ...]
    zones: tuple[str, ...]
    cooling_schedule_names: tuple[str, ...]
    heating_schedule_names: tuple[str, ...]
    object_count: int

    def to_dict(self) -> dict:
        data = asdict(self)
        data["model_path"] = str(self.model_path)
        return data


def _without_comments(text: str) -> str:
    return "\n".join(line.split("!", 1)[0] for line in text.splitlines())


def parse_idf_objects(text: str) -> tuple[IDFObject, ...]:
    """Parse IDF objects by semicolon boundaries without global substitutions."""
    objects: list[IDFObject] = []
    start = 0
    for match in re.finditer(r";", text):
        end = match.end()
        raw = text[start:end]
        clean = _without_comments(raw).strip()
        start = end
        if not clean or "," not in clean:
            continue
        fields = tuple(part.strip() for part in clean[:-1].split(","))
        object_type = fields[0] if fields else ""
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9:._-]*", object_type):
            continue
        objects.append(
            IDFObject(
                object_type=object_type,
                fields=fields,
                raw_text=raw,
                start=end - len(raw),
                end=end,
            )
        )
    return tuple(objects)


def _case_map(objects: Iterable[IDFObject]) -> dict[str, IDFObject]:
    return {item.name.casefold(): item for item in objects if item.name}


def _schedule_reference(
    item: IDFObject,
    purpose: str,
    schedule: str | None = None,
    zones: tuple[str, ...] = (),
    strategy: str = "preserve",
    note: str = "Object fields were inspected without numeric replacement.",
) -> ScheduleReference:
    return ScheduleReference(
        object_type=item.object_type,
        object_name=item.name,
        referenced_schedule=schedule,
        referenced_zones=zones,
        probable_purpose=purpose,
        modification_strategy=strategy,
        assumption_note=note,
    )


def inspect_baseline_model(model_path: Path) -> BaselineModelInspection:
    """Return a structured inventory of Phase 5-relevant IDF objects."""
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"EnergyPlus model does not exist: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    objects = parse_idf_objects(text)
    schedule_objects = tuple(
        item for item in objects
        if item.object_type.casefold() in {
            "schedule:compact", "schedule:ruleset", "schedule:constant"
        }
    )
    schedules = tuple(
        _schedule_reference(
            item,
            "schedule",
            strategy=(
                "preserve; Phase 5 adds uniquely named thermostat schedules"
            ),
        )
        for item in schedule_objects
    )
    thermostat_setpoints = tuple(
        item for item in objects
        if item.object_type.casefold().startswith("thermostatsetpoint:")
    )
    setpoint_by_name = _case_map(thermostat_setpoints)
    thermostat_controls = tuple(
        item for item in objects
        if item.object_type.casefold() == "zonecontrol:thermostat"
    )
    thermostat_refs: list[ThermostatReference] = []
    heating_schedules: set[str] = set()
    cooling_schedules: set[str] = set()
    for control in thermostat_controls:
        zone = control.fields[2] if len(control.fields) > 2 else ""
        setpoint_names: list[str] = []
        heating: str | None = None
        cooling: str | None = None
        for index in range(4, len(control.fields) - 1, 2):
            object_type = control.fields[index]
            object_name = control.fields[index + 1]
            if not object_name:
                continue
            setpoint_names.append(object_name)
            setpoint = setpoint_by_name.get(object_name.casefold())
            if setpoint is None:
                continue
            kind = object_type.casefold()
            if kind.endswith("singleheating") and len(setpoint.fields) > 2:
                heating = setpoint.fields[2]
            elif kind.endswith("singlecooling") and len(setpoint.fields) > 2:
                cooling = setpoint.fields[2]
            elif kind.endswith("dualsetpoint"):
                if len(setpoint.fields) > 2:
                    heating = setpoint.fields[2]
                if len(setpoint.fields) > 3:
                    cooling = setpoint.fields[3]
        if heating:
            heating_schedules.add(heating)
        if cooling:
            cooling_schedules.add(cooling)
        thermostat_refs.append(
            ThermostatReference(
                object_type=control.object_type,
                object_name=control.name,
                referenced_schedule=(
                    control.fields[3] if len(control.fields) > 3 else None
                ),
                referenced_zones=(zone,) if zone else (),
                probable_purpose="conditioned-zone thermostat control",
                modification_strategy=(
                    "retarget referenced thermostat-setpoint objects to "
                    "EcoPilot baseline schedules"
                ),
                assumption_note=(
                    "Only setpoint references used by ZoneControl:Thermostat "
                    "objects are modified."
                ),
                heating_schedule_name=heating,
                cooling_schedule_name=cooling,
                setpoint_object_names=tuple(setpoint_names),
            )
        )

    people = tuple(
        item for item in objects if item.object_type.casefold() == "people"
    )
    occupancy_refs: list[OccupancyReference] = []
    people_refs: list[ScheduleReference] = []
    for item in people:
        zone = item.fields[2] if len(item.fields) > 2 else ""
        schedule = item.fields[3] if len(item.fields) > 3 else None
        design_people = None
        if len(item.fields) > 5:
            try:
                design_people = float(item.fields[5])
            except ValueError:
                design_people = None
        occupancy_refs.append(
            OccupancyReference(
                object_type=item.object_type,
                object_name=item.name,
                referenced_schedule=schedule,
                referenced_zones=(zone,) if zone else (),
                probable_purpose="real EnergyPlus people occupancy",
                modification_strategy="preserve and freeze in manifest",
                assumption_note=(
                    "The existing example-model occupancy pattern is retained."
                ),
                design_people=design_people,
            )
        )
        people_refs.append(
            _schedule_reference(
                item, "people internal load", schedule, (zone,) if zone else ()
            )
        )

    def load_references(object_type: str, purpose: str) -> tuple[ScheduleReference, ...]:
        result = []
        for item in objects:
            if item.object_type.casefold() != object_type.casefold():
                continue
            zone = item.fields[2] if len(item.fields) > 2 else ""
            schedule = item.fields[3] if len(item.fields) > 3 else None
            result.append(
                _schedule_reference(
                    item, purpose, schedule, (zone,) if zone else ()
                )
            )
        return tuple(result)

    hvac_schedules = tuple(
        _schedule_reference(item, "HVAC availability schedule")
        for item in schedule_objects
        if "avail" in item.name.casefold()
        or item.name.casefold() in {"plantonsched", "min oa sched"}
    )
    output_requests = tuple(
        _schedule_reference(item, "EnergyPlus output request")
        for item in objects
        if item.object_type.casefold().startswith("output:")
    )
    zones = tuple(
        item.name for item in objects
        if item.object_type.casefold() == "zone" and item.name
    )
    return BaselineModelInspection(
        model_path=path.resolve(),
        schedules=schedules,
        thermostat_references=tuple(thermostat_refs),
        occupancy_references=tuple(occupancy_refs),
        people_objects=tuple(people_refs),
        lights_objects=load_references("Lights", "lighting internal load"),
        electric_equipment_objects=load_references(
            "ElectricEquipment", "electric-equipment internal load"
        ),
        hvac_availability_schedules=hvac_schedules,
        output_requests=output_requests,
        run_periods=tuple(
            item.fields for item in objects
            if item.object_type.casefold() == "runperiod"
        ),
        timesteps=tuple(
            item.fields for item in objects
            if item.object_type.casefold() == "timestep"
        ),
        zones=zones,
        cooling_schedule_names=tuple(sorted(cooling_schedules, key=str.casefold)),
        heating_schedule_names=tuple(sorted(heating_schedules, key=str.casefold)),
        object_count=len(objects),
    )


__all__ = [
    "BaselineModelInspection",
    "IDFObject",
    "OccupancyReference",
    "ScheduleReference",
    "ThermostatReference",
    "inspect_baseline_model",
    "parse_idf_objects",
]
