"""Phase 12 AI Copilot chat experience."""

import asyncio
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any

import streamlit as st

from llm.client import OllamaClient
from llm.mcp_client import MCPBridge
from llm.settings import LLM_SETTINGS
from ui.components import status_badge

from .components import product_header
from .copilot_service import (
    SUGGESTED_QUESTIONS,
    CopilotAnswer,
    build_replay_answer,
    compact_answer_metadata,
    run_live_question,
)
from .data import DEMO_MODE_LIVE, DEMO_MODE_REPLAY, ArtifactLoadError, load_demo_context


@dataclass(frozen=True)
class LiveReadiness:
    ollama_available: bool
    model_available: bool
    mcp_available: bool
    artifact_available: bool
    diagnostics: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return (
            self.ollama_available
            and self.model_available
            and self.mcp_available
            and self.artifact_available
        )


async def _check_mcp_readiness() -> bool:
    bridge = MCPBridge(LLM_SETTINGS)
    async with bridge.connect():
        return bool(bridge.tools_by_name)


@st.cache_data(ttl=30, max_entries=1, show_spinner=False)
def check_live_readiness() -> LiveReadiness:
    """Check existing local service boundaries without generating a response."""
    diagnostics: list[str] = []
    artifact_available = False
    try:
        load_demo_context()
        artifact_available = True
    except ArtifactLoadError as exc:
        diagnostics.append(f"Artifact: {exc.public_message}")

    ollama_available = False
    model_available = False
    try:
        readiness = OllamaClient(LLM_SETTINGS).discover()
        ollama_available = bool(readiness.available)
        model_available = bool(readiness.model_installed)
        diagnostics.extend(str(item) for item in readiness.readiness_issues)
    except Exception as exc:
        diagnostics.append(f"Ollama: {type(exc).__name__}: {exc}")

    mcp_available = False
    try:
        mcp_available = asyncio.run(
            asyncio.wait_for(_check_mcp_readiness(), timeout=15)
        )
    except Exception as exc:
        diagnostics.append(f"MCP: {type(exc).__name__}: {exc}")

    return LiveReadiness(
        ollama_available=ollama_available,
        model_available=model_available,
        mcp_available=mcp_available,
        artifact_available=artifact_available,
        diagnostics=tuple(diagnostics),
    )


def _serialize_answer(answer: CopilotAnswer) -> dict[str, Any]:
    value = asdict(answer)
    value["tools_used"] = list(answer.tools_used)
    value["artifacts"] = list(answer.artifacts)
    return value


def _answer_from_state(value: dict[str, Any]) -> CopilotAnswer:
    return CopilotAnswer(
        content=str(value["content"]),
        model=str(value["model"]),
        source_mode=str(value["source_mode"]),
        tools_used=tuple(value.get("tools_used", [])),
        latency_seconds=float(value.get("latency_seconds", 0)),
        safety_classification=str(value["safety_classification"]),
        artifacts=tuple(value.get("artifacts", [])),
        advisory_proposal=value.get("advisory_proposal"),
        error_code=value.get("error_code"),
    )


def _render_answer(
    streamlit: Any,
    answer: CopilotAnswer,
    *,
    message_key: str,
) -> None:
    streamlit.write(answer.content)
    with streamlit.container(horizontal=True, gap="small"):
        status_badge(streamlit, answer.source_mode, status="info")
        status_badge(
            streamlit,
            answer.safety_classification,
            status="error" if answer.error_code else "verified",
        )
    streamlit.caption(
        f"Model · {answer.model} · response latency "
        f"{answer.latency_seconds:.2f} s"
    )
    if answer.tools_used:
        with streamlit.expander(
            "MCP tools used",
            icon=":material/hub:",
        ):
            for tool in answer.tools_used:
                streamlit.code(tool, language="text")
    if answer.advisory_proposal:
        with streamlit.expander(
            "Structured advisory proposal",
            icon=":material/data_object:",
        ):
            streamlit.json(answer.advisory_proposal, expanded=False)
            streamlit.warning(
                "This proposal is advisory and was not applied. Deterministic "
                "safety logic retains final authority."
            )
    if answer.artifacts:
        with streamlit.expander(
            "Internal evidence citations",
            icon=":material/folder_open:",
        ):
            for artifact in answer.artifacts:
                streamlit.code(artifact, language="text")
    if answer.error_code:
        if answer.source_mode == "Live Services":
            streamlit.error(
                "The live request stopped safely. Your question is retained and "
                "no action was applied."
            )
            if streamlit.button(
                "Use Verified Demo Replay",
                icon=":material/replay:",
                key=f"use-replay-{message_key}",
            ):
                streamlit.session_state["demo_source_mode"] = DEMO_MODE_REPLAY
                streamlit.rerun()
        else:
            streamlit.error(
                "Verified replay could not answer because its saved evidence "
                "is unavailable. No response was fabricated."
            )
        with streamlit.expander(
            "Technical diagnostics",
            icon=":material/troubleshoot:",
        ):
            streamlit.code(compact_answer_metadata(answer), language="json")


def render_ai_copilot(streamlit: Any) -> None:
    mode = streamlit.session_state.get("demo_source_mode", DEMO_MODE_REPLAY)
    streamlit.session_state.setdefault("copilot_messages", [])
    streamlit.session_state.setdefault("copilot_pending_prompt", None)

    product_header(
        streamlit,
        title="Ask EcoPilot",
        subtitle=(
            "Question-answering over bounded EnergyPlus evidence, saved control "
            "history, and the existing local qwen3:4b + MCP boundary."
        ),
        eyebrow="AI Copilot",
        mode=mode,
    )
    streamlit.caption(
        "LLM provides advisory reasoning. Deterministic safety logic retains "
        "final authority. No hidden chain-of-thought or system prompt is displayed."
    )

    live_readiness = None
    if mode == DEMO_MODE_REPLAY:
        streamlit.info(
            "Suggested questions return deterministic answers built strictly "
            "from verified Phase 7–10 artifacts. No new Ollama or MCP call occurs.",
            icon=":material/replay:",
        )
    else:
        live_readiness = check_live_readiness()
        if live_readiness.ready:
            streamlit.success(
                "**LIVE READY**  \nqwen3:4b connected · MCP ready",
                icon=":material/check_circle:",
            )
        else:
            streamlit.warning(
                "**LIVE UNAVAILABLE**  \nLive qwen3:4b is currently unavailable. "
                "Verified Demo Replay remains available.",
                icon=":material/cloud_off:",
            )
            if live_readiness.diagnostics:
                with streamlit.expander(
                    "Technical diagnostics",
                    icon=":material/troubleshoot:",
                ):
                    for item in live_readiness.diagnostics:
                        streamlit.code(item, language="text")
        streamlit.caption(
            "Live Services calls local qwen3:4b and read-only MCP tools only after "
            "you submit a question. Control requests remain advisory and cannot "
            "write directly to an actuator."
        )

    if not streamlit.session_state["copilot_messages"]:
        selected = streamlit.pills(
            "Suggested questions",
            SUGGESTED_QUESTIONS,
            selection_mode="single",
            key="copilot_suggestion",
            disabled=bool(
                mode == DEMO_MODE_LIVE
                and live_readiness is not None
                and not live_readiness.ready
            ),
        )
        if selected:
            streamlit.session_state["copilot_pending_prompt"] = selected

    with streamlit.container(horizontal=True):
        if streamlit.button(
            "Clear chat",
            icon=":material/delete_sweep:",
            key="clear-copilot-chat",
        ):
            streamlit.session_state["copilot_messages"] = []
            streamlit.session_state["copilot_pending_prompt"] = None
            streamlit.rerun()
        streamlit.page_link(
            "app_pages/phase7.py",
            label="Open Phase 7 technical evidence",
            icon=":material/open_in_new:",
        )
        streamlit.page_link(
            "app_pages/phase8.py",
            label="Open validated runtime workflow",
            icon=":material/shield:",
        )

    for message_index, message in enumerate(
        streamlit.session_state["copilot_messages"]
    ):
        with streamlit.chat_message(message["role"]):
            if message["role"] == "assistant":
                _render_answer(
                    streamlit,
                    _answer_from_state(message["answer"]),
                    message_key=f"history-{message_index}",
                )
            else:
                streamlit.write(message["content"])

    live_unavailable = bool(
        mode == DEMO_MODE_LIVE
        and live_readiness is not None
        and not live_readiness.ready
    )
    typed_prompt = streamlit.chat_input(
        (
            "Live service unavailable · use Verified Demo Replay"
            if live_unavailable
            else "Ask about energy, comfort, safety, demand, or control history"
        ),
        key="copilot_chat_input",
        max_chars=600,
        submit_mode="disable",
        disabled=live_unavailable,
    )
    prompt = typed_prompt or streamlit.session_state.pop(
        "copilot_pending_prompt",
        None,
    )
    if not prompt:
        return

    streamlit.session_state["copilot_messages"].append(
        {"role": "user", "content": prompt}
    )
    with streamlit.chat_message("user"):
        streamlit.write(prompt)

    with streamlit.chat_message("assistant"):
        if mode == DEMO_MODE_LIVE:
            with streamlit.status(
                "Consulting approved building tools…",
                expanded=True,
            ) as status:
                answer = run_live_question(prompt)
                status.update(
                    label=(
                        "Live response complete"
                        if answer.error_code is None
                        else "Live response stopped safely"
                    ),
                    state="complete" if answer.error_code is None else "error",
                )
        else:
            try:
                answer = build_replay_answer(prompt, load_demo_context())
            except ArtifactLoadError as exc:
                answer = CopilotAnswer(
                    content=(
                        f"Verified replay is unavailable: {exc.public_message} "
                        "No response was fabricated."
                    ),
                    model="qwen3:4b",
                    source_mode="Verified artifact replay",
                    tools_used=(),
                    latency_seconds=0,
                    safety_classification="Missing evidence",
                    artifacts=(),
                    error_code="MISSING_ARTIFACT",
                )
        _render_answer(
            streamlit,
            answer,
            message_key=f"new-{len(streamlit.session_state['copilot_messages'])}",
        )
    streamlit.session_state["copilot_messages"].append(
        {"role": "assistant", "answer": _serialize_answer(answer)}
    )
    streamlit.rerun()


__all__ = ["LiveReadiness", "check_live_readiness", "render_ai_copilot"]
