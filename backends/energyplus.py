"""Structural placeholder for the Phase 4 EnergyPlus integration."""

from datetime import datetime
from pathlib import Path

import pandas as pd

from schemas import BuildingState, ControlAction, RuntimeErrorRecord

_NOT_IMPLEMENTED = "EnergyPlus integration will be implemented in Phase 4."


class EnergyPlusBackend:
    """Future primary high-fidelity application backend.

    Phase 4 responsibilities will include running an IDF with an EPW through the
    EnergyPlus runtime/API; streaming zone temperature, facility electricity,
    occupancy, supported indoor-air-quality values, PMV/comfort outputs, and peak
    demand; capturing structured runtime errors; exposing setpoint actuators;
    applying validated supervisory overrides; and writing versioned modified IDFs.

    This class deliberately performs none of those jobs yet and never silently
    substitutes the lightweight simulator.
    """

    def __init__(
        self,
        executable_path: str | Path = "",
        idf_path: str | Path = "",
        epw_path: str | Path = "",
        output_directory: str | Path = "energyplus/output",
    ) -> None:
        self.executable_path = Path(executable_path) if executable_path else None
        self.idf_path = Path(idf_path) if idf_path else None
        self.epw_path = Path(epw_path) if epw_path else None
        self.output_directory = Path(output_directory)

    @property
    def backend_name(self) -> str:
        return "energyplus"

    @property
    def data_source_label(self) -> str:
        return "EnergyPlus"

    @property
    def is_available(self) -> bool:
        return False

    @staticmethod
    def _not_implemented() -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def reset(self) -> None:
        self._not_implemented()

    def get_current_timestamp(self) -> datetime:
        self._not_implemented()

    def is_complete(self) -> bool:
        self._not_implemented()

    def step(
        self,
        actions: dict[str, ControlAction] | None = None,
    ) -> list[BuildingState]:
        self._not_implemented()

    def history_dataframe(self) -> pd.DataFrame:
        self._not_implemented()

    def get_runtime_errors(self) -> list[RuntimeErrorRecord]:
        self._not_implemented()
