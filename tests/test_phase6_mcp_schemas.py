from datetime import datetime
import pytest
from pydantic import ValidationError
from mcp_service.schemas import BaselineRunRequest, ZoneTelemetryRequest


def test_valid_strict_requests():
    request = ZoneTelemetryRequest(
        zone_name="SPACE1-1", start=datetime(2000, 1, 1),
        end=datetime(2000, 1, 2), aggregation="hourly", limit=10,
    )
    assert request.limit == 10
    assert BaselineRunRequest().force_rebuild is False


def test_invalid_range_aggregation_and_extra_path():
    with pytest.raises(ValidationError):
        ZoneTelemetryRequest(zone_name="x", aggregation="weekly", limit=1)
    with pytest.raises(ValidationError):
        BaselineRunRequest(model_path="unsafe.idf")
