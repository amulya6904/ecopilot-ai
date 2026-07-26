import pytest

from comparison.energy import calculate_energy_metrics
from tests.phase10_helpers import aligned_frames


@pytest.mark.parametrize(
    ("controlled", "expected_sign"),
    [((9.0, 9.0), 1), ((10.0, 10.0), 0), ((11.0, 11.0), -1)],
)
def test_positive_zero_and_negative_energy_results(controlled, expected_sign):
    result = aligned_frames(controlled_energy=controlled)
    _, _, metrics, frame = calculate_energy_metrics(result.facility)
    reduction = metrics[0].absolute_reduction
    assert (reduction > 0) - (reduction < 0) == expected_sign
    assert len(frame) == 2


def test_zero_baseline_denominator_is_rejected():
    result = aligned_frames(baseline_energy=(0.0, 0.0))
    with pytest.raises(ValueError):
        calculate_energy_metrics(result.facility)
