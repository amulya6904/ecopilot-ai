"""Single, local CSS injection point for the EcoPilot presentation shell."""

from pathlib import Path
from typing import Any

from .tokens import TOKENS


PROJECT_ROOT = Path(__file__).parents[1]
STYLESHEET = PROJECT_ROOT / "assets" / "ecopilot.css"


def build_stylesheet() -> str:
    """Build the local stylesheet from semantic Python tokens."""
    css = STYLESHEET.read_text(encoding="utf-8")
    return f"<style>\n:root {{\n{TOKENS.css_variables()}\n}}\n{css}\n</style>"


def apply_theme(streamlit: Any) -> None:
    """Inject the application stylesheet once from the root entry point."""
    streamlit.html(build_stylesheet())


__all__ = ["STYLESHEET", "apply_theme", "build_stylesheet"]
