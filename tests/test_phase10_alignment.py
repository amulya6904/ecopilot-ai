import pandas as pd

from comparison.alignment import align_telemetry
from comparison.normalization import normalize_facility, normalize_zone
from tests.phase10_helpers import aligned_frames, facility_frame, zone_frame


def test_full_alignment():
    result = aligned_frames()
    assert result.report["complete"]
    assert result.report["alignment_percentage"] == 100.0


def test_missing_interval_and_wrong_frequency_are_reported():
    baseline = normalize_facility(
        facility_frame(), run_id="b", classification="b"
    )
    controlled_raw = facility_frame().iloc[[0]].copy()
    controlled = normalize_facility(
        controlled_raw, run_id="c", classification="c"
    )
    zone = normalize_zone(zone_frame(), run_id="b")
    result = align_telemetry(
        baseline, controlled, zone, zone, expected_intervals=2
    )
    assert not result.report["complete"]
    assert result.report["missing_controlled_intervals"] == 1


def test_duplicate_counts_are_audited():
    result = aligned_frames()
    duplicate = pd.concat([result.facility.iloc[:2], result.facility.iloc[[0]]])
    assert duplicate.duplicated(["timestamp"]).sum() == 1
