from comparison.cost import calculate_cost_metrics
from comparison.settings import ComparisonSettings
from tests.phase10_helpers import aligned_frames
from comparison.energy import calculate_energy_metrics


def test_flat_and_time_of_use_cost_assumptions(tmp_path):
    aligned = aligned_frames()
    *_, energy = calculate_energy_metrics(aligned.facility)
    flat, frame = calculate_cost_metrics(
        energy,
        settings=ComparisonSettings(
            repository_root=tmp_path, flat_tariff_per_kwh=2.0
        ),
    )
    assert flat["absolute_cost_reduction"] == 4.0
    tou, _ = calculate_cost_metrics(
        energy,
        settings=ComparisonSettings(
            repository_root=tmp_path,
            electricity_tariff_mode="time_of_use",
            time_of_use_tariff_by_hour=tuple(float(hour + 1) for hour in range(24)),
        ),
    )
    assert tou["cost_reduction_percent"] == 10.0
    assert len(frame) == 2
