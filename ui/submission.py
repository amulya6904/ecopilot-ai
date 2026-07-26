"""Submission readiness page backed by the repository checklist."""

from pathlib import Path
from typing import Any

from .artifact_views import PROJECT_ROOT
from .components import badge_row, render_error_state


def render_submission_checklist(streamlit: Any) -> None:
    streamlit.title("Submission checklist")
    streamlit.caption(
        "Final packaging readiness with measured-result and scope disclosures."
    )
    badge_row(streamlit, ("Complete", "Reproducible", "Official EnergyPlus"))
    checklist = PROJECT_ROOT / "docs" / "SUBMISSION_CHECKLIST.md"
    if not checklist.is_file():
        render_error_state(
            streamlit,
            title="Submission checklist missing",
            explanation="The expected repository checklist is unavailable.",
            affected_feature="Final submission readiness",
            next_step="Restore docs/SUBMISSION_CHECKLIST.md and refresh.",
        )
        return
    streamlit.markdown(checklist.read_text(encoding="utf-8"))
    streamlit.download_button(
        "Download checklist",
        checklist.read_bytes(),
        file_name="SUBMISSION_CHECKLIST.md",
        mime="text/markdown",
        icon=":material/download:",
    )


__all__ = ["render_submission_checklist"]
