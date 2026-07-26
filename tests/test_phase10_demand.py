from comparison.demand import calculate_demand_metrics
from comparison.settings import ComparisonSettings
from tests.phase10_helpers import aligned_frames


def test_peak_reduction_increase_and_threshold_counts(tmp_path):
    result = aligned_frames()
    result.facility["facility_demand_kw_baseline"] = [5.0, 10.0]
    result.facility["facility_demand_kw_controlled"] = [6.0, 9.0]
    settings = ComparisonSettings(
        repository_root=tmp_path, demand_warning_kw=6.0,
        demand_critical_kw=9.0,
    )
    summary, frame = calculate_demand_metrics(
        result.facility, settings=settings
    )
    assert summary["absolute_peak_reduction_kw"] == 1.0
    assert summary["controlled_intervals_above_critical"] == 1
    result.facility["facility_demand_kw_controlled"] = [6.0, 11.0]
    increased, _ = calculate_demand_metrics(
        result.facility, settings=settings
    )
    assert increased["absolute_peak_reduction_kw"] == -1.0
    assert len(frame) == 2
