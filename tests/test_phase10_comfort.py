from comparison.comfort import calculate_comfort_metrics
from comparison.normalization import normalize_zone
from comparison.alignment import align_telemetry
from comparison.normalization import normalize_facility
from comparison.settings import ComparisonSettings
from tests.phase10_helpers import facility_frame, zone_frame


def _comfort_alignment(base, controlled):
    facility = normalize_facility(
        facility_frame(), run_id="r", classification="r"
    )
    return align_telemetry(
        facility,
        facility,
        normalize_zone(base, run_id="b"),
        normalize_zone(controlled, run_id="c"),
        expected_intervals=2,
    ).zone


def test_occupied_only_proxy_comfort_and_degree_hours(tmp_path):
    baseline = zone_frame((21.0, 26.0), (0.0, 1.0))
    controlled = zone_frame((21.0, 24.0), (0.0, 1.0))
    first, second, summary, _ = calculate_comfort_metrics(
        _comfort_alignment(baseline, controlled),
        settings=ComparisonSettings(repository_root=tmp_path),
    )
    assert first.occupied_records == 1
    assert first.degree_hours_outside_comfort == 1.0
    assert second.temperature_compliance_percent == 100.0
    assert second.pmv_available is False
    assert summary["comfort_gate_passed"]


def test_genuine_pmv_is_used_only_when_present(tmp_path):
    base = zone_frame(pmv=(0.0, 0.8), ppd=(5.0, 25.0))
    controlled = zone_frame(pmv=(0.1, 0.2), ppd=(6.0, 7.0))
    first, second, _, _ = calculate_comfort_metrics(
        _comfort_alignment(base, controlled),
        settings=ComparisonSettings(repository_root=tmp_path),
    )
    assert first.pmv_available and second.pmv_available
    assert first.pmv_compliance_percent == 50.0
