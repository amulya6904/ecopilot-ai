"""Full-day orchestration for the Phase 2 lightweight development simulator."""

from dataclasses import asdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config.settings import SIMULATION, SIMULATOR_PHYSICS
from config.zones import ZONES
from simulator.models import HVACAction, ZoneState
from simulator.occupancy import generate_occupancy
from simulator.weather import generate_environment
from simulator.zone import ZoneSimulator

HISTORY_COLUMNS = [
    "timestamp", "zone_id", "zone_name", "indoor_temperature_c",
    "outdoor_temperature_c", "humidity_percent", "occupancy", "co2_ppm",
    "hvac_setpoint_c", "fan_speed_percent", "ventilation_level",
    "hvac_power_kw", "interval_energy_kwh", "cumulative_energy_kwh",
    "comfort_status", "electricity_price_per_kwh",
    "carbon_intensity_g_per_kwh",
]


class BuildingSimulator:
    """Orchestrate environment, occupancy, and independent zone simulation."""

    def __init__(self, random_seed: int = 42, heat_wave: bool = False) -> None:
        self.random_seed = random_seed
        self.heat_wave = heat_wave
        self.start_timestamp = datetime(2026, 7, 25, SIMULATION.start_hour)
        self.history: list[ZoneState] = []
        self.current_step_index = 0
        self._initialize_random_streams_and_zones()

    def _initialize_random_streams_and_zones(self) -> None:
        seed_sequence = np.random.SeedSequence(self.random_seed)
        child_seeds = seed_sequence.spawn(1 + 2 * len(ZONES))
        self._weather_rng = np.random.default_rng(child_seeds[0])
        self._occupancy_rngs: dict[str, np.random.Generator] = {}
        self.zones: dict[str, ZoneSimulator] = {}
        for index, (zone_id, configuration) in enumerate(ZONES.items()):
            self._occupancy_rngs[zone_id] = np.random.default_rng(
                child_seeds[1 + 2 * index]
            )
            zone_rng = np.random.default_rng(child_seeds[2 + 2 * index])
            self.zones[zone_id] = ZoneSimulator(
                zone_id, configuration, zone_rng, SIMULATION.step_minutes
            )

    @property
    def current_timestamp(self) -> datetime:
        """Return timestamp of the next interval to be simulated."""
        return self.start_timestamp + timedelta(
            minutes=self.current_step_index * SIMULATION.step_minutes
        )

    @property
    def is_complete(self) -> bool:
        """Return whether all configured intervals have been simulated."""
        return self.current_step_index >= SIMULATION.total_steps

    def default_actions(self) -> dict[str, HVACAction]:
        """Return fixed Phase 2 test actions for every zone."""
        return {
            zone_id: HVACAction(
                setpoint_c=SIMULATOR_PHYSICS.default_setpoint_c,
                fan_speed_percent=SIMULATOR_PHYSICS.default_fan_speed_percent,
                ventilation_level=SIMULATOR_PHYSICS.default_ventilation_level,
            )
            for zone_id in ZONES
        }

    def step(
        self, actions: dict[str, HVACAction] | None = None
    ) -> list[ZoneState]:
        """Advance all zones through one shared environment interval."""
        if self.is_complete:
            raise RuntimeError("The full-day simulation is already complete.")
        supplied_actions = {} if actions is None else actions
        unknown_ids = set(supplied_actions) - set(ZONES)
        if unknown_ids:
            raise ValueError(f"Unknown action zone IDs: {sorted(unknown_ids)}")
        effective_actions = self.default_actions()
        effective_actions.update(supplied_actions)

        timestamp = self.current_timestamp
        environment = generate_environment(timestamp, self._weather_rng, self.heat_wave)
        interval_states: list[ZoneState] = []
        for zone_id, zone in self.zones.items():
            occupancy = generate_occupancy(
                zone_id,
                timestamp,
                ZONES[zone_id]["maximum_occupancy"],
                self._occupancy_rngs[zone_id],
            )
            interval_states.append(zone.step(
                timestamp, environment, occupancy, effective_actions[zone_id]
            ))
        self.history.extend(interval_states)
        self.current_step_index += 1
        return interval_states

    def run_full_day(
        self, actions: dict[str, HVACAction] | None = None
    ) -> pd.DataFrame:
        """Run all remaining intervals with fixed externally supplied actions."""
        while not self.is_complete:
            self.step(actions)
        return self.history_dataframe()

    def history_dataframe(self) -> pd.DataFrame:
        """Return sorted simulation history with stable types and columns."""
        frame = pd.DataFrame(
            (asdict(record) for record in self.history),
            columns=HISTORY_COLUMNS,
        )
        if frame.empty:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"])
            return frame
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        return frame.sort_values(
            ["timestamp", "zone_id"], ignore_index=True
        )[HISTORY_COLUMNS]

    def reset(self) -> None:
        """Clear history and recreate all seeded random streams and zone states."""
        self.history.clear()
        self.current_step_index = 0
        self._initialize_random_streams_and_zones()
