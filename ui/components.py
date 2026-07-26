"""Reusable native Streamlit components for consistent Phase 11 pages."""

from collections.abc import Callable, Iterable
from typing import Any

from .constants import PhasePageSpec


BADGE_COLORS = {
    "Verified": "green",
    "Complete": "green",
    "Available": "green",
    "Unavailable": "gray",
    "Development only": "orange",
    "Official EnergyPlus": "blue",
    "Advisory only": "violet",
    "Safety supervised": "green",
    "Reproducible": "green",
    "Assumption based": "orange",
    "Not claimed": "gray",
    "Failed": "red",
    "Configuration foundation": "blue",
    "Verified local MCP": "blue",
}


def badge(streamlit: Any, label: str) -> None:
    streamlit.badge(
        label,
        color=BADGE_COLORS.get(label, "gray"),
    )


def badge_row(streamlit: Any, labels: Iterable[str]) -> None:
    with streamlit.container(horizontal=True):
        for label in labels:
            badge(streamlit, label)


def render_error_state(
    streamlit: Any,
    *,
    title: str,
    explanation: str,
    affected_feature: str,
    next_step: str,
    diagnostics: str | None = None,
) -> None:
    streamlit.error(f"**{title}** — {explanation}", icon=":material/error:")
    streamlit.write(f"**Affected feature:** {affected_feature}")
    streamlit.write(f"**Safe next step:** {next_step}")
    if diagnostics:
        with streamlit.expander(
            "Technical diagnostics",
            icon=":material/troubleshoot:",
        ):
            streamlit.code(diagnostics, language="text")


def render_phase_intro(streamlit: Any, spec: PhasePageSpec) -> None:
    streamlit.title(spec.title)
    streamlit.caption(spec.objective)
    badge_row(streamlit, (spec.classification, spec.status))
    columns = streamlit.columns(2, border=True)
    with columns[0]:
        streamlit.markdown("**Verified**")
        for item in spec.verified:
            streamlit.markdown(f"- {item}")
    with columns[1]:
        streamlit.markdown("**Intentionally not claimed**")
        streamlit.write(spec.not_claimed)
    with streamlit.container(horizontal=True):
        with streamlit.container(border=True):
            streamlit.markdown("**Primary controls**")
            streamlit.caption(spec.primary_controls)
        with streamlit.container(border=True):
            streamlit.markdown("**Main evidence**")
            streamlit.caption(spec.evidence)


def render_phase_page(
    streamlit: Any,
    spec: PhasePageSpec,
    renderer: Callable[[], None],
) -> None:
    render_phase_intro(streamlit, spec)
    judge_mode = bool(streamlit.session_state.get("judge_mode", False))
    show_full = True
    if judge_mode and not spec.judge_priority:
        streamlit.info(
            "Judge Mode is showing the verified summary. The full technical "
            "page remains available below and never starts a run automatically.",
            icon=":material/visibility:",
        )
        show_full = streamlit.toggle(
            "Show full technical evidence",
            value=False,
            key=f"{spec.key}_show_full_evidence",
        )
        if not show_full:
            streamlit.dataframe(
                [
                    {"Evidence location": item}
                    for item in spec.artifacts
                ],
                hide_index=True,
                width="stretch",
            )
    if show_full:
        renderer()
    with streamlit.container(border=True):
        streamlit.markdown("**Next logical step**")
        streamlit.write(spec.next_step)


__all__ = [
    "BADGE_COLORS",
    "badge",
    "badge_row",
    "render_error_state",
    "render_phase_intro",
    "render_phase_page",
]
