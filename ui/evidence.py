"""Central project-scoped evidence catalogue and download page."""

from itertools import groupby
from pathlib import Path
from typing import Any

import pandas as pd

from .artifact_views import evidence_records, is_approved_display_path
from .components import render_error_state


def render_evidence(streamlit: Any) -> None:
    streamlit.title("Evidence & downloads")
    streamlit.caption(
        "Verified artifacts are displayed with project-relative paths. Files "
        "outside approved repository evidence roots are never exposed."
    )
    records = evidence_records()
    if not records:
        render_error_state(
            streamlit,
            title="No evidence catalogue available",
            explanation="No approved Phase 5–10 artifacts were discovered.",
            affected_feature="Evidence table and downloads",
            next_step="Run the documented validation scripts and refresh.",
        )
        return

    for group_name, grouped in groupby(
        sorted(records, key=lambda item: (item.group, item.name)),
        key=lambda item: item.group,
    ):
        group_records = list(grouped)
        streamlit.subheader(group_name)
        streamlit.dataframe(
            pd.DataFrame(
                [
                    {
                        "Artifact": item.name,
                        "Classification": item.classification,
                        "Run ID": item.run_id,
                        "Timestamp": item.timestamp,
                        "Success": item.success,
                        "Source": item.source,
                        "Path": item.display_path,
                    }
                    for item in group_records
                ]
            ),
            hide_index=True,
            width="stretch",
            column_config={
                "Success": streamlit.column_config.CheckboxColumn("Success"),
                "Path": streamlit.column_config.TextColumn("Project path"),
            },
        )
        with streamlit.container(horizontal=True):
            for item in group_records:
                path = Path(item.path)
                if (
                    path.is_file()
                    and is_approved_display_path(path)
                    and path.stat().st_size <= 25_000_000
                ):
                    streamlit.download_button(
                        item.name,
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime=(
                            "application/json"
                            if path.suffix == ".json"
                            else "text/markdown"
                            if path.suffix == ".md"
                            else "text/plain"
                        ),
                        key=f"evidence_download_{item.group}_{path.name}",
                        icon=":material/download:",
                    )


__all__ = ["render_evidence"]
