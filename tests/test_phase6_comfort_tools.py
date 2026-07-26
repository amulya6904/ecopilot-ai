from mcp_service.tools.comfort_tools import get_comfort_summary, get_thermostat_adherence


def test_pmv_null_and_adherence(phase6_context):
    comfort = get_comfort_summary(phase6_context)["data"]
    assert comfort["pmv_available"] is False
    assert comfort["pmv_compliance_percent"] is None
    adherence = get_thermostat_adherence(phase6_context)["data"]
    assert adherence["adherence_percent"] == 100.0
    assert len(adherence["boundary_samples"]) <= 20
