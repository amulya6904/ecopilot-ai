"""Runtime discovery and deterministic selection of real EnergyPlus actuators."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from .api_loader import load_energyplus_api
from .settings import PHASE8_SETTINGS, Phase8Settings
from .variable_discovery import request_runtime_variables


@dataclass(frozen=True)
class ActuatorDescriptor:
    what: str
    component_type: str
    control_type: str
    actuator_key: str
    unit: str

    @property
    def identifier(self) -> str:
        return (
            f"{self.component_type}|{self.control_type}|{self.actuator_key}"
        )


class ActuatorSelectionError(ValueError):
    pass


def filter_actuators(records: Iterable[Any]) -> list[ActuatorDescriptor]:
    return sorted(
        [
            ActuatorDescriptor(
                what=str(record.what),
                component_type=str(record.name),
                control_type=str(record.type),
                actuator_key=str(record.key),
                unit=str(record.unit),
            )
            for record in records
            if str(getattr(record, "what", "")).casefold() == "actuator"
        ],
        key=lambda item: (
            item.component_type.casefold(),
            item.control_type.casefold(),
            item.actuator_key.casefold(),
        ),
    )


def _cooling_score(
    item: ActuatorDescriptor,
    settings: Phase8Settings,
) -> int:
    component = item.component_type.casefold()
    control = item.control_type.casefold()
    key = item.actuator_key.casefold()
    unit = item.unit.casefold().strip("[] ")
    exact_zone_cooling = (
        component == "zone temperature control"
        and control == "cooling setpoint"
        and key == settings.controlled_zone.casefold()
    )
    zone_cooling = (
        component == "zone temperature control"
        and control == "cooling setpoint"
    )
    exact_schedule = key == settings.controlled_schedule_name.casefold()
    cooling_schedule = (
        component.startswith("schedule:")
        and control == "schedule value"
        and any(word in key for word in ("cool", "clg"))
    )
    if not (zone_cooling or exact_schedule or cooling_schedule):
        return -1
    if (
        not exact_schedule
        and "temperature" not in unit
        and unit not in {"c", "degc"}
    ):
        return -1
    score = 0
    if exact_zone_cooling:
        score += 200
    if exact_schedule:
        score += 100
    if any(word in key for word in ("cool", "clg", "cooling_setpoint")):
        score += 50
    if component.startswith("schedule:"):
        score += 20
    if control == "schedule value":
        score += 20
    if zone_cooling:
        score += 40
    return score if score >= 40 else -1


def cooling_setpoint_candidates(
    inventory: Iterable[ActuatorDescriptor],
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> list[ActuatorDescriptor]:
    scored = [
        (_cooling_score(item, settings), item)
        for item in inventory
    ]
    return [
        item
        for score, item in sorted(
            (pair for pair in scored if pair[0] >= 0),
            key=lambda pair: (
                -pair[0],
                pair[1].component_type.casefold(),
                pair[1].control_type.casefold(),
                pair[1].actuator_key.casefold(),
            ),
        )
    ]


def select_cooling_setpoint_actuator(
    inventory: Iterable[ActuatorDescriptor],
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> ActuatorDescriptor:
    candidates = cooling_setpoint_candidates(inventory, settings)
    if not candidates:
        raise ActuatorSelectionError(
            "No discovered actuator is a verified cooling-setpoint candidate."
        )
    top_score = _cooling_score(candidates[0], settings)
    ties = [
        item
        for item in candidates
        if _cooling_score(item, settings) == top_score
    ]
    if len(ties) != 1:
        raise ActuatorSelectionError(
            "Cooling actuator selection is ambiguous: "
            + ", ".join(item.identifier for item in ties)
        )
    return candidates[0]


def discover_available_actuators(
    settings: Phase8Settings = PHASE8_SETTINGS,
    *,
    save_path: Path | None = None,
) -> dict[str, Any]:
    api, availability = load_energyplus_api(settings)
    if api is None or not availability.available:
        result = {
            "success": False,
            "availability": asdict(availability),
            "actuators": [],
            "candidates": [],
            "selected_actuator": None,
            "errors": list(availability.readiness_issues),
        }
        destination = (
            settings.resolve(save_path)
            if save_path is not None
            else settings.resolve(settings.official_inventory_path)
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(result, indent=2, default=str, allow_nan=False),
            encoding="utf-8",
        )
        result["artifact_path"] = str(destination)
        return result
    inventory: list[ActuatorDescriptor] = []
    callback_errors: list[str] = []
    state = api.state_manager.new_state()
    discovered = False
    request_runtime_variables(api.exchange, state, settings)

    def callback(runtime_state: Any) -> None:
        nonlocal inventory, discovered
        try:
            if discovered or not api.exchange.api_data_fully_ready(runtime_state):
                return
            inventory = filter_actuators(api.exchange.get_api_data(runtime_state))
            discovered = True
        except Exception as exc:
            callback_errors.append(f"{type(exc).__name__}: {exc}")
            api.runtime.stop_simulation(runtime_state)

    api.runtime.callback_after_predictor_before_hvac_managers(state, callback)
    output = settings.resolve(settings.output_root) / "discovery"
    output.mkdir(parents=True, exist_ok=True)
    args = [
        "-d",
        str(output),
        "-w",
        str(settings.resolve(settings.weather_file_path)),
        str(settings.resolve(settings.runtime_model_path)),
    ]
    exit_code = api.runtime.run_energyplus(state, args)
    api.state_manager.delete_state(state)
    candidates = cooling_setpoint_candidates(inventory, settings)
    selected: ActuatorDescriptor | None = None
    errors = list(callback_errors)
    try:
        selected = select_cooling_setpoint_actuator(inventory, settings)
    except ActuatorSelectionError as exc:
        errors.append(str(exc))
    result: dict[str, Any] = {
        "success": (
            exit_code == 0
            and discovered
            and selected is not None
            and not callback_errors
        ),
        "availability": asdict(availability),
        "EnergyPlus_exit_code": exit_code,
        "inventory_count": len(inventory),
        "actuators": [asdict(item) | {"identifier": item.identifier} for item in inventory],
        "candidates": [asdict(item) | {"identifier": item.identifier} for item in candidates],
        "selected_actuator": (
            asdict(selected) | {"identifier": selected.identifier}
            if selected
            else None
        ),
        "selection_policy": (
            "Select the unique highest-scoring discovered temperature actuator; "
            "an exact ECOPILOT_BASELINE_COOLING_SCHEDULE key outranks other "
            "cooling/CLG schedule or thermostat candidates. Ties are rejected."
        ),
        "errors": errors,
    }
    destination = (
        settings.resolve(save_path)
        if save_path is not None
        else settings.resolve(settings.official_inventory_path)
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, indent=2, default=str, allow_nan=False),
        encoding="utf-8",
    )
    result["artifact_path"] = str(destination)
    return result


__all__ = [
    "ActuatorDescriptor",
    "ActuatorSelectionError",
    "cooling_setpoint_candidates",
    "discover_available_actuators",
    "filter_actuators",
    "select_cooling_setpoint_actuator",
]
