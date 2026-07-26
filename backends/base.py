"""Application-facing building backend contract."""

from datetime import datetime
from typing import Protocol, runtime_checkable

import pandas as pd

from schemas import BuildingState, ControlAction, RuntimeErrorRecord


@runtime_checkable
class BuildingBackend(Protocol):
    """Common contract for development and future high-fidelity backends."""

    @property
    def backend_name(self) -> str:
        ...

    @property
    def data_source_label(self) -> str:
        ...

    @property
    def is_available(self) -> bool:
        ...

    def reset(self) -> None:
        ...

    def get_current_timestamp(self) -> datetime:
        ...

    def is_complete(self) -> bool:
        ...

    def step(
        self,
        actions: dict[str, ControlAction] | None = None,
    ) -> list[BuildingState]:
        ...

    def history_dataframe(self) -> pd.DataFrame:
        ...

    def get_runtime_errors(self) -> list[RuntimeErrorRecord]:
        ...
