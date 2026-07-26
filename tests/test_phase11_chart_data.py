import pandas as pd

from ui.artifact_views import (
    latest_phase10_directory,
    load_phase10_bundle,
    load_phase10_event_timeline,
)
from ui.charts import downsample_for_display
from ui.phase10 import build_action_impact_table, meaningful_action_windows


def test_display_sampling_preserves_source_and_exact_final_row():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=8760, freq="h"),
            "value": range(8760),
        }
    )
    original = frame.copy()
    sampled = downsample_for_display(frame, maximum_rows=2400)
    pd.testing.assert_frame_equal(frame, original)
    assert len(sampled) <= 2401
    assert sampled.iloc[-1].to_dict() == frame.iloc[-1].to_dict()


def test_action_display_limit_does_not_change_full_resolution_metrics():
    directory = latest_phase10_directory(require_reproducible=True)
    assert directory is not None
    bundle = load_phase10_bundle(str(directory.resolve()))
    table = build_action_impact_table(
        bundle["actions"],
        bundle["energy"],
        bundle["comfort"],
    )
    display = meaningful_action_windows(table, limit=24)
    assert len(table) == 155
    assert len(display) == 24
    assert len(bundle["energy"]) == 8760
    assert bundle["summary"]["energy_reduction_kwh"] == 5.626075812324416


def test_fallback_timeline_reads_persisted_project_scoped_events():
    directory = latest_phase10_directory(require_reproducible=True)
    assert directory is not None
    events = load_phase10_event_timeline(str(directory.resolve()))
    assert len(events) == 521
    assert set(events["event_type"]) == {"Fallback"}
    assert events["timestamp"].notna().all()
