"""Application-shell state and sidebar presentation."""

from pathlib import Path
from typing import Any

from .components import status_badge
from .demo.data import DEMO_MODE_LIVE, DEMO_MODE_REPLAY


LOGO_PATH = Path(__file__).parents[1] / "assets" / "logo_mark.svg"


def initialize_shell_state(streamlit: Any) -> None:
    """Initialize presentation-only state without touching runtime control."""
    streamlit.session_state.setdefault("judge_mode", True)
    streamlit.session_state.setdefault("developer_mode", False)
    streamlit.session_state.setdefault("demo_source_mode", DEMO_MODE_REPLAY)


def is_judge_mode(streamlit: Any) -> bool:
    return bool(streamlit.session_state.get("judge_mode", True))


def _judge_mode_changed(streamlit: Any) -> None:
    streamlit.session_state["developer_mode"] = not bool(
        streamlit.session_state["judge_mode"]
    )


def _developer_mode_changed(streamlit: Any) -> None:
    streamlit.session_state["judge_mode"] = not bool(
        streamlit.session_state["developer_mode"]
    )


def render_sidebar(streamlit: Any) -> None:
    """Render the persistent mode control and exact offline footer."""
    with streamlit.sidebar:
        if is_judge_mode(streamlit):
            status_badge(streamlit, "Verified artifact mode", status="verified")
            streamlit.caption("Verified Demo Replay · presentation ready")
        else:
            status_badge(streamlit, "Developer Mode", status="info")
            streamlit.caption(
                "Preserved technical pages and explicit run controls available"
            )
        with streamlit.expander(
            "Demo & runtime settings",
            expanded=False,
            icon=":material/tune:",
        ):
            streamlit.toggle(
                "Judge Mode",
                key="judge_mode",
                on_change=_judge_mode_changed,
                args=(streamlit,),
                help=(
                    "Use verified persisted artifacts and hide expensive execution "
                    "controls. Turn off for Developer Mode diagnostics."
                ),
            )
            streamlit.toggle(
                "Developer Mode",
                key="developer_mode",
                on_change=_developer_mode_changed,
                args=(streamlit,),
                help=(
                    "Expose the preserved Phase 1–11 technical pages and run controls."
                ),
            )
            streamlit.selectbox(
                "Data source",
                (DEMO_MODE_REPLAY, DEMO_MODE_LIVE),
                key="demo_source_mode",
                help=(
                    "Replay reads verified saved artifacts. Live Services is opt-in "
                    "and runs only after a separate explicit action."
                ),
            )
            if streamlit.session_state["demo_source_mode"] == DEMO_MODE_LIVE:
                streamlit.warning(
                    "Live Services is enabled. Readiness is checked before "
                    "the Copilot input is enabled."
                )
            else:
                streamlit.caption("Default · deterministic · no Ollama required")
        streamlit.markdown("**EcoPilot AI**")
        streamlit.caption("EnergyPlus + MCP + qwen3:4b")
        streamlit.caption("Offline PoC")


__all__ = [
    "LOGO_PATH",
    "initialize_shell_state",
    "is_judge_mode",
    "render_sidebar",
]
