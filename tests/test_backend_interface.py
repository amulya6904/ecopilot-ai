"""Contract and registry tests for application-facing building backends."""

import pytest

from backends import create_backend, get_backend_status
from backends.base import BuildingBackend
from backends.energyplus import EnergyPlusBackend
from backends.lightweight import LightweightSimulatorBackend


def test_backend_status_is_explicit_and_honest() -> None:
    status = get_backend_status()
    assert status["lightweight"] == {
        "available": True,
        "label": "Lightweight Development Simulator",
    }
    assert isinstance(status["energyplus"]["available"], bool)
    assert status["energyplus"]["label"] == "EnergyPlus Official Backend"
    if not status["energyplus"]["available"]:
        assert status["energyplus"]["reason"]


def test_registry_creates_only_the_requested_backend() -> None:
    lightweight = create_backend("lightweight", random_seed=42)
    energyplus = create_backend("energyplus")
    assert isinstance(lightweight, LightweightSimulatorBackend)
    assert isinstance(lightweight, BuildingBackend)
    assert isinstance(energyplus, EnergyPlusBackend)
    assert not isinstance(energyplus, LightweightSimulatorBackend)
    with pytest.raises(ValueError, match="Unknown building backend"):
        create_backend("unknown")
