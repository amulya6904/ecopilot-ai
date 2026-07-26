"""Conventional fixed-schedule HVAC benchmark controller."""

from datetime import datetime, time

from config.settings import BASELINE
from config.zones import ZONES
from schemas.control_action import ControlAction
from simulator.models import HVACAction


class BaselineController:
    """Fixed-schedule HVAC controller used as the development benchmark."""

    def is_scheduled_occupied(self, timestamp: datetime, zone_id: str) -> bool:
        """Return whether a zone is inside its configured operating schedule."""
        if zone_id not in ZONES:
            raise ValueError(f"Unknown zone ID: {zone_id}")
        zone = ZONES[zone_id]
        start = time(zone["normal_start_hour"])
        end = time(zone["normal_end_hour"])
        return start <= timestamp.time() < end

    def action_for(self, timestamp: datetime, zone_id: str) -> HVACAction:
        """Return the configured action based only on time and zone ID."""
        if self.is_scheduled_occupied(timestamp, zone_id):
            return HVACAction(
                BASELINE.occupied_setpoint_c,
                BASELINE.occupied_fan_speed_percent,
                BASELINE.occupied_ventilation,
            )
        return HVACAction(
            BASELINE.unoccupied_setpoint_c,
            BASELINE.unoccupied_fan_speed_percent,
            BASELINE.unoccupied_ventilation,
        )

    def actions_for_building(self, timestamp: datetime) -> dict[str, HVACAction]:
        """Return fixed-schedule actions for every configured zone."""
        return {zone_id: self.action_for(timestamp, zone_id) for zone_id in ZONES}

    def control_action_for(self, timestamp: datetime, zone_id: str) -> ControlAction:
        """Return the same schedule decision in the shared control schema."""

        action = self.action_for(timestamp, zone_id)
        return ControlAction(
            zone_id=zone_id,
            cooling_setpoint_c=action.setpoint_c,
            fan_speed_percent=float(action.fan_speed_percent),
            ventilation_level=action.ventilation_level,
            action_source="baseline_schedule",
            reason="Configured occupied/unoccupied development baseline schedule.",
            requested_at=timestamp,
            validated=True,
            validation_message="Validated by static baseline configuration.",
        )

    def control_actions_for_building(
        self, timestamp: datetime
    ) -> dict[str, ControlAction]:
        """Return shared-schema baseline actions for every configured zone."""

        return {
            zone_id: self.control_action_for(timestamp, zone_id)
            for zone_id in ZONES
        }


def run_baseline_day(
    simulator: "BuildingSimulator", controller: BaselineController
) -> "pd.DataFrame":
    """Run remaining simulator intervals using timestamp-specific baseline actions."""
    while not simulator.is_complete:
        actions = controller.actions_for_building(simulator.current_timestamp)
        simulator.step(actions)
    return simulator.history_dataframe()


# Imports used only after definitions avoid coupling controller construction to pandas.
import pandas as pd  # noqa: E402
from simulator.building import BuildingSimulator  # noqa: E402
