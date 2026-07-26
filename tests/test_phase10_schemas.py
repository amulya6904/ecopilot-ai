import pytest
from pydantic import ValidationError

from comparison.schemas import ComparisonMetric


def test_phase10_schemas_are_strict_and_forbid_extra_fields():
    metric = ComparisonMetric(
        metric="Energy",
        baseline=10.0,
        controlled=9.0,
        absolute_reduction=1.0,
        reduction_percent=10.0,
        unit="kWh",
        available=True,
    )
    assert metric.reduction_percent == 10.0
    with pytest.raises(ValidationError):
        ComparisonMetric(
            metric="Energy",
            baseline=10.0,
            controlled=9.0,
            absolute_reduction=1.0,
            reduction_percent=10.0,
            unit="kWh",
            available=True,
            invented=True,
        )
