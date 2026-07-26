import pandas as pd
import pytest

from comparison.normalization import (
    normalize_actions,
    normalize_facility,
    normalize_zone,
)
from tests.phase10_helpers import facility_frame, zone_frame


def test_units_timestamps_zone_mapping_and_no_facility_duplication():
    facility = normalize_facility(
        facility_frame(), run_id="r", classification="official"
    )
    zone = normalize_zone(zone_frame(), run_id="r")
    assert len(facility) == 2
    assert pd.api.types.is_datetime64_any_dtype(facility["timestamp"])
    assert zone.loc[0, "display_zone_name"] == "Open Office"
    assert zone["comfort_method"].eq("occupied_temperature_proxy").all()


def test_duplicate_facility_and_zone_records_are_rejected():
    duplicate = pd.concat([facility_frame(), facility_frame().iloc[[0]]])
    with pytest.raises(ValueError):
        normalize_facility(duplicate, run_id="r", classification="official")
    duplicate_zone = pd.concat([zone_frame(), zone_frame().iloc[[0]]])
    with pytest.raises(ValueError):
        normalize_zone(duplicate_zone, run_id="r")


def test_action_aliases_and_nulls_are_normalized():
    actions = normalize_actions(pd.DataFrame([{
        "simulation_timestamp": "2000-01-01T01:00:00",
        "action_id": "a",
        "requested_value": 22.5,
        "approved_value": 22.5,
        "applied_value": 22.5,
        "observed_setpoint_after_application": None,
    }]))
    assert actions.loc[0, "requested_setpoint_c"] == 22.5
    assert pd.isna(actions.loc[0, "observed_setpoint_c"])
