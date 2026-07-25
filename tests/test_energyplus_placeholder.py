"""Tests that keep the EnergyPlus boundary honest until Phase 4."""

import pytest

from backends.energyplus import EnergyPlusBackend


def test_energyplus_placeholder_identity_and_availability() -> None:
    backend = EnergyPlusBackend()
    assert backend.backend_name == "energyplus"
    assert backend.data_source_label == "EnergyPlus"
    assert backend.is_available is False


@pytest.mark.parametrize(
    "operation",
    [
        lambda backend: backend.reset(),
        lambda backend: backend.get_current_timestamp(),
        lambda backend: backend.is_complete(),
        lambda backend: backend.step(),
        lambda backend: backend.history_dataframe(),
        lambda backend: backend.get_runtime_errors(),
    ],
)
def test_runtime_operations_raise_phase4_placeholder(operation) -> None:
    with pytest.raises(
        NotImplementedError,
        match="EnergyPlus integration will be implemented in Phase 4",
    ):
        operation(EnergyPlusBackend())
