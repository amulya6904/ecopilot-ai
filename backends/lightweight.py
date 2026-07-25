"""Adapter for the existing lightweight development simulator."""

from dataclasses import asdict
from datetime import datetime

import pandas as pd

from schemas import (
    BuildingState,
    ControlAction,
    RuntimeErrorRecord,
    from_lightweight_zone_state,
    to_lightweight_hvac_action,
)
from simulator.building import BuildingSimulator


class LightweightSimulatorBackend:
    """Compose the Phase 2 simulator behind the shared backend interface.

    The adapter changes no simulator equations, timing, random streams, heat-wave
    behavior, or existing history representation.
    """

    def __init__(
        self,
        random_seed: int = 42,
        heat_wave: bool = False,
        simulator: BuildingSimulator | None = None,
    ) -> None:
        self.simulator = (
            BuildingSimulator(random_seed=random_seed, heat_wave=heat_wave)
            if simulator is None
            else simulator
        )
        self._runtime_errors: list[RuntimeErrorRecord] = []

    @property
    def backend_name(self) -> str:
        return "lightweight"

    @property
    def data_source_label(self) -> str:
        return "Lightweight Development Simulator"

    @property
    def is_available(self) -> bool:
        return True

    def reset(self) -> None:
        self.simulator.reset()
        self._runtime_errors.clear()

    def get_current_timestamp(self) -> datetime:
        return self.simulator.current_timestamp

    def is_complete(self) -> bool:
        return self.simulator.is_complete

    def _record_failure(self, error: Exception) -> None:
        self._runtime_errors.append(
            RuntimeErrorRecord(
                timestamp=self.simulator.current_timestamp,
                source=self.backend_name,
                severity="error",
                code=type(error).__name__,
                message=str(error),
                raw_log_excerpt=None,
                recoverable=False,
            )
        )

    def step(
        self,
        actions: dict[str, ControlAction] | None = None,
    ) -> list[BuildingState]:
        converted = None
        if actions is not None:
            converted = {
                zone_id: to_lightweight_hvac_action(action)
                for zone_id, action in actions.items()
            }
        try:
            return [
                from_lightweight_zone_state(state)
                for state in self.simulator.step(converted)
            ]
        except Exception as error:
            self._record_failure(error)
            raise

    def run_full_day(
        self,
        actions: dict[str, ControlAction] | None = None,
    ) -> pd.DataFrame:
        """Run all remaining intervals and return backend-neutral telemetry."""

        while not self.is_complete():
            self.step(actions)
        return self.history_dataframe()

    def history_dataframe(self) -> pd.DataFrame:
        states = [
            from_lightweight_zone_state(state) for state in self.simulator.history
        ]
        frame = pd.DataFrame(asdict(state) for state in states)
        if frame.empty:
            frame = pd.DataFrame(columns=BuildingState.__dataclass_fields__)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        return frame.sort_values(
            ["timestamp", "zone_id"], ignore_index=True
        )

    def get_runtime_errors(self) -> list[RuntimeErrorRecord]:
        return list(self._runtime_errors)
