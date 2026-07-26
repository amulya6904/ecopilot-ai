"""EnergyPlus installation-aware placeholder for the current Phase 4 setup step."""

from dataclasses import asdict, replace
from datetime import datetime
import json
from pathlib import Path

import pandas as pd

from config.settings import ENERGYPLUS, EnergyPlusSettings
from energyplus.adapter.discovery import EnergyPlusAvailability, discover_energyplus
from energyplus.adapter.error_parser import parse_energyplus_error_file
from energyplus.adapter.runner import EnergyPlusRunResult, run_energyplus
from energyplus.adapter.telemetry import (
    EnergyPlusTelemetrySummary,
    parse_energyplus_outputs,
)
from schemas import BuildingState, ControlAction, RuntimeErrorRecord

_NOT_IMPLEMENTED = (
    "EnergyPlus simulation execution is not implemented in the current setup step."
)


class EnergyPlusBackend:
    """Expose installation and readiness without running or falling back."""

    backend_id = "energyplus"
    display_name = "EnergyPlus Official Backend"

    def __init__(
        self,
        settings: EnergyPlusSettings | None = None,
        executable_path: str | Path = "",
        idf_path: str | Path = "",
        epw_path: str | Path = "",
        output_directory: str | Path = "",
    ) -> None:
        resolved = settings or ENERGYPLUS
        overrides = {}
        if executable_path:
            overrides["executable_path"] = Path(executable_path)
        if idf_path:
            overrides["base_model_path"] = Path(idf_path)
        if epw_path:
            overrides["weather_file_path"] = Path(epw_path)
        if output_directory:
            overrides["output_root"] = Path(output_directory)
        self.settings = replace(resolved, **overrides)
        self._last_result: EnergyPlusRunResult | None = None
        self._history = pd.DataFrame()
        self._building_history = pd.DataFrame()
        self._summary: EnergyPlusTelemetrySummary | None = None
        self._runtime_errors: list[RuntimeErrorRecord] = []

    @property
    def backend_name(self) -> str:
        return self.backend_id

    @property
    def data_source_label(self) -> str:
        return self.display_name

    def availability_status(self) -> EnergyPlusAvailability:
        return discover_energyplus(self.settings)

    @property
    def installation_detected(self) -> bool:
        return self.availability_status().installed

    @property
    def is_available(self) -> bool:
        """Whether the complete simulation environment is runnable."""
        return self.availability_status().ready_for_run

    def run_simulation(self) -> EnergyPlusRunResult:
        """Run the explicit EnergyPlus backend and retain parsed Phase 4 state."""
        result = run_energyplus(self.settings)
        self._last_result = result
        self._runtime_errors = (
            list(parse_energyplus_error_file(result.error_file_path).records)
            if result.error_file_path else []
        )
        if result.success and result.csv_output_path:
            telemetry = parse_energyplus_outputs(result.csv_output_path)
            self._history = telemetry.zone
            self._building_history = telemetry.building
            self._summary = telemetry.summary
            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            metadata["telemetry"] = asdict(telemetry.summary)
            result.metadata_path.write_text(
                json.dumps(metadata, indent=2),
                encoding="utf-8",
            )
        else:
            self._history = pd.DataFrame()
            self._building_history = pd.DataFrame()
            self._summary = None
        return result

    def get_last_run_result(self) -> EnergyPlusRunResult | None:
        return self._last_result

    def get_telemetry_summary(self) -> EnergyPlusTelemetrySummary | None:
        return self._summary

    def building_history_dataframe(self) -> pd.DataFrame:
        return self._building_history.copy()

    @staticmethod
    def _not_implemented() -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def reset(self) -> None:
        self._last_result = None
        self._history = pd.DataFrame()
        self._building_history = pd.DataFrame()
        self._summary = None
        self._runtime_errors.clear()

    def get_current_timestamp(self) -> datetime:
        if self._last_result is None:
            raise RuntimeError("No EnergyPlus run has completed.")
        return datetime.fromtimestamp(
            self._last_result.metadata_path.stat().st_mtime
        )

    def is_complete(self) -> bool:
        return self._last_result is not None

    def step(
        self,
        actions: dict[str, ControlAction] | None = None,
    ) -> list[BuildingState]:
        self._not_implemented()

    def history_dataframe(self) -> pd.DataFrame:
        return self._history.copy()

    def get_runtime_errors(self) -> list[RuntimeErrorRecord]:
        return list(self._runtime_errors)
