"""Backend-neutral supervisory control proposals."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.models import HVACAction


@dataclass(frozen=True)
class ControlAction:
    """A traceable requested control action for one zone.

    No Phase 1-3 caller should label an action as AI-generated. Baseline schedule
    actions use ``baseline_schedule`` and fixed harness actions use
    ``fixed_test_action``.
    """

    zone_id: str
    cooling_setpoint_c: float
    heating_setpoint_c: float | None = None
    fan_speed_percent: float | None = None
    ventilation_level: str | None = None
    action_source: str = "fixed_test_action"
    reason: str = ""
    confidence: float | None = None
    requested_at: datetime | None = None
    validated: bool = False
    validation_message: str = ""

    def __post_init__(self) -> None:
        if not self.zone_id.strip():
            raise ValueError("zone_id is required.")
        if not self.action_source.strip():
            raise ValueError("action_source is required.")
        if not isfinite(self.cooling_setpoint_c):
            raise ValueError("cooling_setpoint_c must be finite.")
        if self.heating_setpoint_c is not None and not isfinite(self.heating_setpoint_c):
            raise ValueError("heating_setpoint_c must be finite when provided.")
        if self.fan_speed_percent is not None:
            if not isfinite(self.fan_speed_percent):
                raise ValueError("fan_speed_percent must be finite.")
            if not 0 <= self.fan_speed_percent <= 100:
                raise ValueError("fan_speed_percent must be between 0 and 100.")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        if self.requested_at is not None and not isinstance(self.requested_at, datetime):
            raise ValueError("requested_at must be a datetime when provided.")


def to_lightweight_hvac_action(action: ControlAction) -> "HVACAction":
    """Convert a shared action to the existing lightweight simulator action."""

    from config.settings import SIMULATOR_PHYSICS
    from simulator.models import HVACAction

    return HVACAction(
        setpoint_c=action.cooling_setpoint_c,
        fan_speed_percent=int(
            SIMULATOR_PHYSICS.default_fan_speed_percent
            if action.fan_speed_percent is None
            else action.fan_speed_percent
        ),
        ventilation_level=(
            SIMULATOR_PHYSICS.default_ventilation_level
            if action.ventilation_level is None
            else action.ventilation_level
        ),
    )
