"""Developer-oriented index over preserved Phase 1–11 evidence routes."""

from typing import Any

from ui.evidence import render_evidence

from .components import product_header
from .data import DEMO_MODE_REPLAY


def render_technical_evidence(streamlit: Any) -> None:
    product_header(
        streamlit,
        title="Technical Evidence",
        subtitle=(
            "Preserved Phase 1–11 renderers, raw MCP and agent artifacts, "
            "runtime diagnostics, safety matrices, and comparison validity."
        ),
        eyebrow="Developer Mode",
        mode=streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY),
    )
    streamlit.warning(
        "Technical Evidence is proof-oriented. Use the product pages for the "
        "three-minute judge demonstration."
    )
    with streamlit.container(horizontal=True, gap="small"):
        for path, label, icon in (
            ("app_pages/architecture.py", "Architecture", ":material/account_tree:"),
            ("app_pages/demo_flow.py", "Phase 11 demo flow", ":material/play_circle:"),
            ("app_pages/phase7.py", "Phase 7 LLM", ":material/psychology:"),
            ("app_pages/phase8.py", "Phase 8 runtime", ":material/tune:"),
            ("app_pages/phase9.py", "Phase 9 safety", ":material/shield:"),
            ("app_pages/phase10.py", "Phase 10 comparison", ":material/analytics:"),
        ):
            streamlit.page_link(path, label=label, icon=icon)
    render_evidence(streamlit)


__all__ = ["render_technical_evidence"]
