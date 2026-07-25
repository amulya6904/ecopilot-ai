"""Environment-portable EnergyPlus backend readiness tests."""

import pytest

from backends import create_backend
from backends.energyplus import EnergyPlusBackend
from backends.lightweight import LightweightSimulatorBackend


def test_energyplus_identity_and_readiness_are_consistent() -> None:
    backend = EnergyPlusBackend()
    status = backend.availability_status()
    assert backend.backend_name == "energyplus"
    assert backend.data_source_label == "EnergyPlus Official Backend"
    assert isinstance(backend.is_available, bool)
    assert backend.is_available is status.ready_for_run
    if status.ready_for_run:
        assert status.installed
        assert status.executable_found
        assert status.idd_found
        assert status.model_exists
        assert status.weather_exists
        assert status.available
    else:
        assert not status.available
        assert status.reason or status.readiness_issues


def test_registry_never_falls_back_to_lightweight() -> None:
    backend = create_backend("energyplus")
    assert isinstance(backend, EnergyPlusBackend)
    assert not isinstance(backend, LightweightSimulatorBackend)


def test_closed_loop_step_remains_unimplemented() -> None:
    with pytest.raises(NotImplementedError, match="simulation execution is not implemented"):
        EnergyPlusBackend().step()
