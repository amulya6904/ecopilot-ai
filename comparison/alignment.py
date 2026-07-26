"""Timestamp, reporting-frequency, and zone alignment for comparable runs."""

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class AlignmentResult:
    facility: pd.DataFrame
    zone: pd.DataFrame
    report: dict[str, Any]


def _frequency_seconds(frame: pd.DataFrame) -> float | None:
    timestamps = (
        pd.Series(pd.to_datetime(frame["timestamp"]))
        .drop_duplicates()
        .sort_values()
    )
    differences = timestamps.diff().dropna().dt.total_seconds()
    return float(differences.mode().iloc[0]) if not differences.empty else None


def align_telemetry(
    baseline_facility: pd.DataFrame,
    controlled_facility: pd.DataFrame,
    baseline_zone: pd.DataFrame,
    controlled_zone: pd.DataFrame,
    *,
    expected_intervals: int,
) -> AlignmentResult:
    """Outer-align first so missing and duplicate records remain auditable."""

    baseline_facility_duplicates = int(
        baseline_facility.duplicated(["timestamp"]).sum()
    )
    controlled_facility_duplicates = int(
        controlled_facility.duplicated(["timestamp"]).sum()
    )
    baseline_zone_duplicates = int(
        baseline_zone.duplicated(
            ["timestamp", "energyplus_zone_name"]
        ).sum()
    )
    controlled_zone_duplicates = int(
        controlled_zone.duplicated(
            ["timestamp", "energyplus_zone_name"]
        ).sum()
    )
    facility = baseline_facility.merge(
        controlled_facility,
        on="timestamp",
        how="outer",
        suffixes=("_baseline", "_controlled"),
        indicator=True,
        validate="one_to_one" if not (
            baseline_facility_duplicates or controlled_facility_duplicates
        ) else "many_to_many",
    )
    zone = baseline_zone.merge(
        controlled_zone,
        on=["timestamp", "energyplus_zone_name"],
        how="outer",
        suffixes=("_baseline", "_controlled"),
        indicator=True,
        validate="one_to_one" if not (
            baseline_zone_duplicates or controlled_zone_duplicates
        ) else "many_to_many",
    )
    matched = int((facility["_merge"] == "both").sum())
    missing_baseline = int((facility["_merge"] == "right_only").sum())
    missing_controlled = int((facility["_merge"] == "left_only").sum())
    expected = max(int(expected_intervals), len(baseline_facility))
    baseline_frequency = _frequency_seconds(baseline_facility)
    controlled_frequency = _frequency_seconds(controlled_facility)
    frequency_match = (
        baseline_frequency is not None
        and baseline_frequency == controlled_frequency
    )
    duplicate_intervals = (
        baseline_facility_duplicates
        + controlled_facility_duplicates
        + baseline_zone_duplicates
        + controlled_zone_duplicates
    )
    percentage = matched / expected * 100 if expected else 0.0
    report = {
        "total_expected_intervals": expected,
        "matched_intervals": matched,
        "missing_baseline_intervals": missing_baseline,
        "missing_controlled_intervals": missing_controlled,
        "duplicate_intervals": duplicate_intervals,
        "baseline_reporting_interval_seconds": baseline_frequency,
        "controlled_reporting_interval_seconds": controlled_frequency,
        "reporting_frequency_match": frequency_match,
        "matched_zone_records": int((zone["_merge"] == "both").sum()),
        "missing_baseline_zone_records": int(
            (zone["_merge"] == "right_only").sum()
        ),
        "missing_controlled_zone_records": int(
            (zone["_merge"] == "left_only").sum()
        ),
        "alignment_percentage": percentage,
        "complete": bool(
            matched == expected
            and not missing_baseline
            and not missing_controlled
            and not duplicate_intervals
            and frequency_match
            and bool((zone["_merge"] == "both").all())
        ),
    }
    return AlignmentResult(
        facility=facility.sort_values(
            "timestamp", kind="stable", ignore_index=True
        ),
        zone=zone.sort_values(
            ["timestamp", "energyplus_zone_name"],
            kind="stable",
            ignore_index=True,
        ),
        report=report,
    )


__all__ = ["AlignmentResult", "align_telemetry"]
