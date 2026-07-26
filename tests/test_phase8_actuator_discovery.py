from types import SimpleNamespace

import pytest

from energyplus.runtime_control.actuator_discovery import (
    ActuatorSelectionError,
    filter_actuators,
    select_cooling_setpoint_actuator,
)
from tests.phase8_helpers import ACTUATOR


def test_filters_real_api_records_and_selects_controlled_zone():
    records = [
        SimpleNamespace(
            what="Actuator", name=ACTUATOR.component_type,
            type=ACTUATOR.control_type, key=ACTUATOR.actuator_key,
            unit=ACTUATOR.unit,
        ),
        SimpleNamespace(
            what="Variable", name="x", type="x", key="x", unit="[C]"
        ),
    ]
    assert select_cooling_setpoint_actuator(filter_actuators(records)) == ACTUATOR


def test_ambiguous_exact_matches_are_rejected():
    with pytest.raises(ActuatorSelectionError):
        select_cooling_setpoint_actuator([ACTUATOR, ACTUATOR])
