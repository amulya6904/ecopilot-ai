"""Streamlit presentation for the advisory-only Phase 7 agent."""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any
import uuid

import pandas as pd

from llm.agent import AdvisoryAgent
from llm.client import OllamaClient
from llm.errors import AgentErrorCode
from llm.mcp_client import MODEL_TOOL_ALLOWLIST
from llm.prompts import DEFAULT_AGENT_TASK, PROMPT_VERSION
from llm.schemas import AgentRunResult
from llm.settings import LLM_SETTINGS
from .artifact_views import PROJECT_ROOT
from .formatting import project_relative


def _timeout_result(agent: AdvisoryAgent, elapsed_ms: float) -> AgentRunResult:
    history = [
        {
            key: event.get(key)
            for key in ("round", "tool", "arguments", "duration_ms", "success")
        }
        for event in agent.bridge.tool_history
    ]
    official_used = any(
        event.get("response", {}).get("metadata", {}).get("classification")
        in {"official_energyplus_baseline", "energyplus_readiness"}
        for event in agent.bridge.tool_history
    )
    return AgentRunResult(
        success=False,
        agent_run_id=f"timeout-{uuid.uuid4().hex[:8]}",
        provider=LLM_SETTINGS.provider,
        model=LLM_SETTINGS.model,
        prompt_version=PROMPT_VERSION,
        proposal=None,
        validation=None,
        tool_history=history,
        retry_count=0,
        context_characters=0,
        evidence_retrieval_mode="deterministic_required_mcp_plan",
        proposal_source="none",
        fallback_used=False,
        llm_completed=False,
        final_prompt_characters=0,
        final_schema_characters=0,
        generated_token_cap=LLM_SETTINGS.num_predict,
        ollama_readiness_ms=0,
        initial_tool_selection_inference_ms=None,
        total_mcp_execution_ms=sum(
            float(event.get("duration_ms") or 0)
            for event in agent.bridge.tool_history
        ),
        final_decision_generation_ms=0,
        validation_ms=0,
        total_run_ms=elapsed_ms,
        artifact_directory=None,
        error_code=AgentErrorCode.AGENT_RUN_TIMEOUT.value,
        error_message=(
            "The local CPU model did not finish within 6 minutes. "
            "No action was applied."
        ),
        official_energyplus_data_used=official_used,
        completed_at=datetime.now(timezone.utc),
    )


async def _run_with_timeout(
    analysis_focus: str,
    progress_callback: Any = None,
) -> AgentRunResult:
    agent = AdvisoryAgent(LLM_SETTINGS)
    started = time.perf_counter()
    try:
        return await asyncio.wait_for(
            agent.run(
                DEFAULT_AGENT_TASK,
                progress_callback=progress_callback,
                analysis_focus=analysis_focus,
            ),
            timeout=LLM_SETTINGS.agent_run_timeout_seconds,
        )
    except TimeoutError:
        return _timeout_result(
            agent,
            (time.perf_counter() - started) * 1000,
        )


def render_phase7(st: Any) -> None:
    st.warning(
        "This workflow produces one advisory proposal. It cannot apply a setpoint, "
        "modify EnergyPlus, execute closed-loop control, or report optimization or savings."
    )
    st.info(
        "Local qwen3:4b inference latency is hardware-dependent. The model runs "
        "outside EnergyPlus callbacks, receives bounded evidence, and has no "
        "direct actuator authority.",
        icon=":material/schedule:",
    )
    readiness = OllamaClient(LLM_SETTINGS).discover()
    status = st.columns(6)
    status[0].metric("Ollama", "Ready" if readiness.available else "Unavailable")
    status[1].metric("Model", LLM_SETTINGS.model)
    status[2].metric("Model installed", "Yes" if readiness.model_installed else "No")
    status[3].metric("MCP", f"{len(MODEL_TOOL_ALLOWLIST)} read-only tools")
    status[4].metric("Advisory only", "Yes")
    status[5].metric("Control execution", "Disabled")
    if readiness.readiness_issues:
        st.info("\n".join(readiness.readiness_issues))

    st.subheader("Agent task")
    st.write(DEFAULT_AGENT_TASK)
    focus = st.text_input(
        "Optional analysis focus",
        help="This is treated only as an advisory focus and cannot override system constraints.",
        max_chars=300,
    )
    if st.button("Run Agent Analysis", type="primary"):
        started = time.perf_counter()
        stage_labels = {
            1: "1/4 Checking Ollama readiness",
            2: "2/4 Retrieving required official evidence through deterministic MCP plan",
            3: "3/4 Generating compact qwen3:4b advisory decision",
            4: "4/4 Running deterministic validation",
        }
        with st.status(stage_labels[1], expanded=True) as run_status:
            progress = st.progress(0.0, text=stage_labels[1])

            def update_progress(stage: int, _message: str) -> None:
                label = stage_labels[stage]
                progress.progress(stage / 4, text=label)
                run_status.update(label=label, state="running")

            result = asyncio.run(_run_with_timeout(focus.strip(), update_progress))
            if result.error_code == AgentErrorCode.AGENT_RUN_TIMEOUT.value:
                progress.empty()
                run_status.update(label="Agent run timed out", state="error", expanded=True)
            elif result.fallback_used:
                progress.empty()
                run_status.update(
                    label="Validated deterministic timeout fallback",
                    state="complete",
                    expanded=True,
                )
            elif result.error_code in {
                AgentErrorCode.MCP_REQUIRED_TOOL_MISSING.value,
                AgentErrorCode.MCP_EVIDENCE_RETRIEVAL_FAILED.value,
                AgentErrorCode.MCP_EVIDENCE_INCOMPLETE.value,
            }:
                progress.empty()
                run_status.update(
                    label="2/4 Required MCP evidence retrieval failed",
                    state="error",
                    expanded=True,
                )
            else:
                progress.empty()
                state = "complete" if result.success else "error"
                label = "Agent analysis complete" if result.success else "Agent analysis stopped"
                run_status.update(label=label, state=state, expanded=not result.success)
        st.session_state["phase7_result"] = result
        st.session_state["phase7_timeout"] = (
            result.error_code == AgentErrorCode.AGENT_RUN_TIMEOUT.value
        )
        st.session_state["phase7_latency_seconds"] = time.perf_counter() - started

    result = st.session_state.get("phase7_result")
    if st.session_state.get("phase7_timeout"):
        st.error(
            f"{AgentErrorCode.AGENT_RUN_TIMEOUT.value}: "
            "The local CPU model did not finish within 6 minutes.\n\n"
            "No action was applied."
        )
        return
    if result is None:
        st.caption("The agent does not run automatically.")
        return
    if result.fallback_used:
        st.warning(
            "qwen3:4b did not finish within the final request limit. "
            "Showing a separately classified, validated deterministic fallback."
        )

    st.subheader("Tool timeline")
    if result.tool_history:
        st.dataframe(pd.DataFrame(result.tool_history), hide_index=True, width="stretch")
    else:
        st.info("No MCP tools were called.")

    proposal = result.proposal
    if proposal is not None:
        st.subheader("Evidence")
        st.dataframe(
            pd.DataFrame([item.model_dump() for item in proposal.evidence]),
            hide_index=True, width="stretch",
        )
        st.subheader("Proposal")
        st.json({
            "zone": f"{proposal.display_zone_name} ({proposal.energyplus_zone_name})",
            "current_setpoint_c": proposal.current_setpoint_c,
            "proposed_setpoint_c": proposal.proposed_setpoint_c,
            "delta_c": proposal.setpoint_change_c,
            "objective": proposal.objective,
            "comfort_risk": proposal.comfort_assessment.risk_level,
            "confidence": proposal.confidence,
            "reason": proposal.reason,
        })
    elif result.error_message:
        st.error(f"{result.error_code}: {result.error_message}")

    st.subheader("Validation")
    st.json({
        "valid": result.validation.valid if result.validation else False,
        "errors": result.validation.validation_errors if result.validation else [],
        "warnings": result.validation.validation_warnings if result.validation else [],
        "retry_count": result.retry_count,
    })
    st.subheader("Classification")
    st.json({
        "classification": (
            "Deterministic timeout fallback"
            if result.fallback_used
            else "LLM advisory proposal"
        ),
        "evidence_retrieval_mode": result.evidence_retrieval_mode,
        "proposal_source": result.proposal_source,
        "fallback_used": result.fallback_used,
        "llm_completed": result.llm_completed,
        "official_energyplus_data_used": result.official_energyplus_data_used,
        "applied_to_energyplus": "No",
        "closed_loop": "No",
        "optimized_result": "No",
        "savings_result": "No",
    })
    st.subheader("Audit")
    st.json({
        "agent_run_id": result.agent_run_id,
        "proposal_id": proposal.proposal_id if proposal else None,
        "artifact_path": (
            project_relative(result.artifact_directory, PROJECT_ROOT)
            if result.artifact_directory
            else None
        ),
        "latency_seconds": round(st.session_state.get("phase7_latency_seconds", 0), 3),
        "model": result.model,
        "prompt_version": result.prompt_version,
        "final_prompt_characters": result.final_prompt_characters,
        "final_schema_characters": result.final_schema_characters,
        "generated_token_cap": result.generated_token_cap,
        "ollama_readiness_ms": round(result.ollama_readiness_ms, 3),
        "initial_tool_selection_inference_ms": (
            None
            if result.initial_tool_selection_inference_ms is None
            else round(result.initial_tool_selection_inference_ms, 3)
        ),
        "total_mcp_execution_ms": round(result.total_mcp_execution_ms, 3),
        "final_decision_generation_ms": round(
            result.final_decision_generation_ms, 3
        ),
        "validation_ms": round(result.validation_ms, 3),
        "total_run_ms": round(result.total_run_ms, 3),
    })


__all__ = ["render_phase7"]
