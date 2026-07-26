from mcp_service.tools.zone_tools import get_zone_summary, get_zone_telemetry, list_zones


def test_alias_plenum_and_limits(phase6_context):
    assert len(list_zones(phase6_context)["data"]["zones"]) == 6
    assert get_zone_summary(phase6_context, "Open Office")["success"]
    plenum = get_zone_summary(phase6_context, "HVAC Plenum")
    assert plenum["data"]["included_in_comfort"] is False
    telemetry = get_zone_telemetry(phase6_context, "SPACE1-1", limit=1)
    assert telemetry["data"]["truncated"] is True


def test_unknown_zone(phase6_context):
    assert get_zone_summary(phase6_context, "../secret")["error"]["code"] == "INVALID_ZONE"
