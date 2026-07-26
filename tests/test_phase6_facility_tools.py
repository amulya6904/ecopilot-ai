from mcp_service.tools.facility_tools import get_facility_summary, get_facility_telemetry


def test_facility_not_duplicated_and_aggregated(phase6_context):
    assert get_facility_summary(phase6_context)["data"]["peak_facility_demand_kw"] == 2.0
    result = get_facility_telemetry(phase6_context, aggregation="daily", limit=10)
    assert result["success"]
    assert result["data"]["facility_values_duplicated_by_zone"] is False
