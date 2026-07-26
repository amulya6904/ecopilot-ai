from comparison.carbon import calculate_carbon_metrics
from comparison.energy import calculate_energy_metrics
from comparison.settings import ComparisonSettings
from tests.phase10_helpers import aligned_frames


def test_constant_and_time_varying_carbon_assumptions(tmp_path):
    aligned = aligned_frames()
    *_, energy = calculate_energy_metrics(aligned.facility)
    constant, frame = calculate_carbon_metrics(
        energy,
        settings=ComparisonSettings(
            repository_root=tmp_path,
            constant_carbon_intensity_g_per_kwh=500.0,
        ),
    )
    assert constant["absolute_carbon_reduction_kg"] == 1.0
    varying, _ = calculate_carbon_metrics(
        energy,
        settings=ComparisonSettings(
            repository_root=tmp_path,
            carbon_intensity_mode="time_varying",
            time_varying_carbon_g_per_kwh_by_hour=tuple(
                500.0 for _ in range(24)
            ),
        ),
    )
    assert varying["carbon_reduction_percent"] == 10.0
    assert len(frame) == 2
