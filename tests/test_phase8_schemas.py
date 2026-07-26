from datetime import timedelta

import pytest

from energyplus.runtime_control.action_provider import build_candidate
from tests.phase8_helpers import ACTUATOR, telemetry


def test_candidate_delta_is_strictly_consistent():
    candidate = build_candidate(telemetry(), ACTUATOR, 23.0, "manual")
    assert candidate.requested_delta_c == 1.0
    with pytest.raises(Exception):
        candidate.model_copy(update={"requested_delta_c": 9}).model_validate(
            candidate.model_copy(update={"requested_delta_c": 9}).model_dump()
        )
