from comparison.reproducibility import compare_repeated_results
from comparison.settings import ComparisonSettings


def test_identical_tolerant_and_mismatched_reproducibility(tmp_path):
    first = {
        "comparison_id": "one",
        "comparison_mode": "reproducible_policy",
        "controlled_energy_kwh": 10.0,
        "controlled_peak_demand_kw": 2.0,
        "controlled_comfort_percent": 90.0,
        "claim_status": "validated_positive_savings",
    }
    second = first | {"comparison_id": "two", "controlled_energy_kwh": 10.0000001}
    identity = {"derived_model_hash": "a", "weather_hash": "b", "interval_count": 2}
    report = compare_repeated_results(
        first,
        second,
        first_identity=identity,
        second_identity=identity,
        first_action_count=1,
        second_action_count=1,
        settings=ComparisonSettings(
            repository_root=tmp_path, reproducibility_tolerance=1e-5
        ),
    )
    assert report.reproducible
    mismatch = compare_repeated_results(
        first,
        second | {"controlled_peak_demand_kw": 3.0},
        first_identity=identity,
        second_identity=identity,
        first_action_count=1,
        second_action_count=2,
        settings=ComparisonSettings(repository_root=tmp_path),
    )
    assert not mismatch.reproducible
