"""Reusable native Streamlit components for EcoPilot's editorial interface."""

from collections.abc import Callable, Iterable
from pathlib import Path
import re
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

STATUS_COLORS = {
    "verified": "green",
    "complete": "green",
    "warning": "orange",
    "error": "red",
    "info": "blue",
    "neutral": "gray",
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def eyebrow(streamlit: Any, text: str) -> None:
    with streamlit.container(key=f"eyebrow-{_slug(text)}"):
        streamlit.caption(text.upper())


def page_header(
    streamlit: Any,
    *,
    title: str,
    subtitle: str,
    label: str | None = None,
) -> None:
    with streamlit.container(key="page-header"):
        if label:
            eyebrow(streamlit, label)
        streamlit.title(title)
        streamlit.write(subtitle)


def status_badge(
    streamlit: Any,
    label: str,
    *,
    status: str = "neutral",
) -> None:
    streamlit.badge(
        label,
        color=STATUS_COLORS.get(status, BADGE_COLORS.get(label, "gray")),
    )


def badge(streamlit: Any, label: str) -> None:
    status_badge(streamlit, label)


def badge_row(streamlit: Any, labels: Iterable[str]) -> None:
    with streamlit.container(horizontal=True):
        for label in labels:
            badge(streamlit, label)


def result_metric(
    streamlit: Any,
    *,
    label: str,
    value: str,
    note: str | None = None,
    primary: bool = False,
) -> None:
    prefix = "primary-result" if primary else "supporting-result"
    key = f"{prefix}-{_slug(label)}"
    with streamlit.container(key=key):
        streamlit.metric(label, value)
        if note:
            streamlit.caption(note)


def compact_metric(
    streamlit: Any,
    *,
    label: str,
    value: str,
    note: str | None = None,
) -> None:
    streamlit.metric(label, value, help=note)


def evidence_row(
    streamlit: Any,
    *,
    title: str,
    phase: str,
    classification: str,
    run_id: str,
    verified: bool,
    description: str,
    relative_path: str,
    download_path: Path | None = None,
    download_key: str | None = None,
) -> None:
    with streamlit.container(key=f"evidence-row-{_slug(title)}"):
        columns = streamlit.columns([3, 2], vertical_alignment="top")
        with columns[0]:
            streamlit.subheader(title)
            with streamlit.container(horizontal=True):
                status_badge(
                    streamlit,
                    "Verified" if verified else "Review",
                    status="verified" if verified else "warning",
                )
                status_badge(streamlit, classification, status="info")
            streamlit.write(description)
        with columns[1]:
            streamlit.caption(f"{phase} · {run_id}")
            streamlit.code(relative_path, language="text")
            if download_path and download_path.is_file():
                streamlit.download_button(
                    "Download artifact",
                    data=download_path.read_bytes(),
                    file_name=download_path.name,
                    mime=_mime_for(download_path),
                    key=download_key or f"download-{_slug(relative_path)}",
                    icon=":material/download:",
                )


def section_divider(
    streamlit: Any,
    title: str | None = None,
    description: str | None = None,
) -> None:
    if title:
        with streamlit.container(key=f"section-opening-{_slug(title)}"):
            streamlit.subheader(title)
            if description:
                streamlit.write(description)
    else:
        streamlit.divider()


def editorial_callout(streamlit: Any, text: str) -> None:
    with streamlit.container(key=f"editorial-callout-{_slug(text)[:48]}"):
        streamlit.markdown(f"**{text}**")


def primary_button(
    streamlit: Any,
    label: str,
    *,
    page: str | None = None,
    key: str | None = None,
    disabled: bool = False,
    help_text: str | None = None,
) -> bool | None:
    if page:
        container_id = key or _slug(label)
        with streamlit.container(key=f"primary-action-{container_id}"):
            streamlit.page_link(
                page,
                label=label,
                icon=":material/arrow_forward:",
                disabled=disabled,
                width="content",
            )
        return None
    return streamlit.button(
        label,
        key=key,
        type="primary",
        disabled=disabled,
        help=help_text,
    )


def secondary_button(
    streamlit: Any,
    label: str,
    *,
    page: str | None = None,
    key: str | None = None,
    disabled: bool = False,
    help_text: str | None = None,
) -> bool | None:
    if page:
        container_id = key or _slug(label)
        with streamlit.container(key=f"secondary-action-{container_id}"):
            streamlit.page_link(
                page,
                label=label,
                icon=":material/arrow_forward:",
                disabled=disabled,
                width="content",
            )
        return None
    return streamlit.button(
        label,
        key=key,
        type="secondary",
        disabled=disabled,
        help=help_text,
    )


def trust_boundary(
    streamlit: Any,
    *,
    title: str,
    description: str,
    authority: str,
) -> None:
    with streamlit.container(key=f"trust-boundary-{_slug(title)}"):
        columns = streamlit.columns([2, 4, 2], vertical_alignment="top")
        columns[0].markdown(f"**{title}**")
        columns[1].write(description)
        with columns[2]:
            status_badge(streamlit, authority, status="verified")


def methodology_item(
    streamlit: Any,
    *,
    label: str,
    value: str,
) -> None:
    with streamlit.container(key=f"methodology-item-{_slug(label)}"):
        columns = streamlit.columns([2, 3], vertical_alignment="top")
        columns[0].caption(label.upper())
        columns[1].write(value)


def artifact_download(
    streamlit: Any,
    *,
    label: str,
    path: Path,
    key: str,
) -> None:
    if not path.is_file():
        empty_state(streamlit, f"{label} is not available.")
        return
    streamlit.download_button(
        label,
        path.read_bytes(),
        file_name=path.name,
        mime=_mime_for(path),
        key=key,
        icon=":material/download:",
    )


def empty_state(streamlit: Any, message: str) -> None:
    streamlit.info(message, icon=":material/info:")


def error_state(
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


def render_error_state(streamlit: Any, **kwargs: Any) -> None:
    error_state(streamlit, **kwargs)


def scope_note(streamlit: Any, text: str) -> None:
    with streamlit.container(key=f"scope-note-{_slug(text)[:48]}"):
        streamlit.markdown(f"**Scope disclosure**  \n{text}")


def _mime_for(path: Path) -> str:
    return {
        ".json": "application/json",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".svg": "image/svg+xml",
        ".zip": "application/zip",
    }.get(path.suffix.lower(), "application/octet-stream")


def render_phase_intro(streamlit: Any, spec: PhasePageSpec) -> None:
    page_header(
        streamlit,
        label=spec.title.split("—", 1)[0].strip(),
        title=spec.title.split("—", 1)[-1].strip(),
        subtitle=spec.objective,
    )
    badge_row(streamlit, (spec.classification, spec.status))
    columns = streamlit.columns([3, 2], vertical_alignment="top")
    with columns[0]:
        section_divider(streamlit, "Primary evidence")
        for item in spec.verified:
            streamlit.markdown(f"- {item}")
        for item in spec.artifacts:
            streamlit.code(item, language="text")
    with columns[1]:
        scope_note(streamlit, spec.not_claimed)


def render_phase_page(
    streamlit: Any,
    spec: PhasePageSpec,
    renderer: Callable[[], None],
) -> None:
    """Wrap working renderers and lock expensive controls in Judge Mode."""
    if spec.judge_priority:
        renderer()
        return
    render_phase_intro(streamlit, spec)
    judge_mode = bool(streamlit.session_state.get("judge_mode", True))
    if judge_mode:
        with streamlit.container(key="mode-locked"):
            streamlit.markdown("**Judge Mode · verified artifacts only**")
            streamlit.write(
                "Execution controls and raw diagnostics are disabled on this "
                "view. Turn off Judge Mode for the complete developer workflow."
            )
        streamlit.page_link(
            "app_pages/evidence.py",
            label="Open Evidence & Downloads",
            icon=":material/folder_open:",
        )
    else:
        with streamlit.expander(
            "Developer controls and technical evidence",
            expanded=False,
            icon=":material/code:",
        ):
            renderer()
    section_divider(streamlit)
    streamlit.markdown("**Next logical step**")
    streamlit.write(spec.next_step)


__all__ = [
    "BADGE_COLORS",
    "artifact_download",
    "badge",
    "badge_row",
    "compact_metric",
    "editorial_callout",
    "empty_state",
    "error_state",
    "evidence_row",
    "eyebrow",
    "methodology_item",
    "page_header",
    "primary_button",
    "render_error_state",
    "render_phase_intro",
    "render_phase_page",
    "result_metric",
    "scope_note",
    "secondary_button",
    "section_divider",
    "status_badge",
    "trust_boundary",
]
