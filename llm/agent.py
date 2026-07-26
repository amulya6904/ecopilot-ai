"""Bounded Phase 7 Ollama-to-MCP advisory agent."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import time
from typing import Any, Callable
import uuid

from pydantic import ValidationError

from llm.audit import AgentAuditWriter
from llm.client import OllamaClient
from llm.decision import (
    assemble_control_proposal,
    build_final_decision_messages,
    build_timeout_fallback_decision,
)
from llm.errors import AgentError, AgentErrorCode
from llm.mcp_client import MCPBridge
from llm.prompts import DEFAULT_AGENT_TASK, PROMPT_VERSION
from llm.retry import can_retry
from llm.schemas import (
    AgentRunResult,
    ControlProposal,
    LLMDecision,
    ProposalValidationResult,
)
from llm.settings import LLMSettings
from llm.validator import VALIDATOR_VERSION, validate_proposal


REQUIRED_EVIDENCE_TOOLS = (
    ("get_official_baseline_summary", {}),
    ("get_facility_summary", {}),
    ("list_zones", {}),
    ("get_comfort_summary", {}),
    ("get_thermostat_adherence", {}),
)
EVIDENCE_RETRIEVAL_MODE = "deterministic_required_mcp_plan"
ProgressCallback = Callable[[int, str], None]


def _run_id() -> str:
    return (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )


class AdvisoryAgent:
    def __init__(
        self,
        settings: LLMSettings,
        llm_client: OllamaClient | Any | None = None,
        bridge: MCPBridge | Any | None = None,
        audit_writer: AgentAuditWriter | None = None,
    ):
        self.settings = settings
        self.llm_client = llm_client or OllamaClient(settings)
        self.bridge = bridge or MCPBridge(settings)
        self.audit_writer = audit_writer or AgentAuditWriter(settings)

    async def _chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        format_schema: dict[str, Any] | None = None,
    ):
        if hasattr(self.llm_client, "chat_async"):
            return await self.llm_client.chat_async(messages, tools, format_schema)
        return await asyncio.to_thread(
            self.llm_client.chat,
            messages,
            tools,
            format_schema,
        )

    async def run(
        self,
        task: str = DEFAULT_AGENT_TASK,
        require_readiness: bool = True,
        progress_callback: ProgressCallback | None = None,
        analysis_focus: str = "",
    ) -> AgentRunResult:
        """Retrieve official evidence, ask for five decisions, then assemble safely."""
        self.bridge.tool_history.clear()
        run_id = _run_id()
        started = time.perf_counter()
        retry_count = 0
        tool_rounds = 0
        proposal: ControlProposal | None = None
        decision: LLMDecision | None = None
        validation: ProposalValidationResult | None = None
        error_code: str | None = None
        error_message: str | None = None
        artifact_directory: str | None = None
        total_tokens = {"prompt": 0, "generation": 0}
        readiness_ms = 0.0
        initial_inference_ms = None
        final_generation_ms = 0.0
        validation_ms = 0.0
        final_prompt = ""
        final_system_prompt = ""
        final_schema = LLMDecision.model_json_schema()
        final_schema_characters = len(
            json.dumps(final_schema, sort_keys=True, separators=(",", ":"))
        )
        final_text = ""
        fallback_used = False
        llm_completed = False
        proposal_source = "none"

        def report(stage: int, message: str) -> None:
            if progress_callback is not None:
                progress_callback(stage, message)

        try:
            if require_readiness:
                report(1, "Checking Ollama readiness")
                readiness_started = time.perf_counter()
                try:
                    readiness = await asyncio.to_thread(self.llm_client.discover)
                finally:
                    readiness_ms = (
                        time.perf_counter() - readiness_started
                    ) * 1000
                if not readiness.available:
                    raise AgentError(
                        AgentErrorCode.OLLAMA_UNAVAILABLE,
                        readiness.reason or "Ollama is unavailable.",
                    )
                if not readiness.model_installed:
                    raise AgentError(
                        AgentErrorCode.MODEL_NOT_INSTALLED,
                        (
                            f"Model {self.settings.model!r} is not installed. "
                            f"Run: ollama pull {self.settings.model}"
                        ),
                    )

            report(
                2,
                "Retrieving required official evidence through deterministic MCP plan",
            )
            async with self.bridge.connect() as bridge:
                missing = [
                    name
                    for name, _ in REQUIRED_EVIDENCE_TOOLS
                    if name not in bridge.tools_by_name
                ]
                if missing:
                    raise AgentError(
                        AgentErrorCode.MCP_REQUIRED_TOOL_MISSING,
                        f"Required MCP evidence tools are missing: {missing}.",
                    )
                for name, arguments in REQUIRED_EVIDENCE_TOOLS:
                    try:
                        await bridge.call_tool(name, arguments, 1)
                    except AgentError as exc:
                        raise AgentError(
                            AgentErrorCode.MCP_EVIDENCE_RETRIEVAL_FAILED,
                            f"Required MCP evidence retrieval failed at {name}: "
                            f"{exc.public_message}",
                        ) from exc
                successful_sequence = [
                    event.get("tool")
                    for event in bridge.tool_history
                    if event.get("success")
                ]
                required_sequence = [
                    name for name, _ in REQUIRED_EVIDENCE_TOOLS
                ]
                if successful_sequence != required_sequence:
                    raise AgentError(
                        AgentErrorCode.MCP_EVIDENCE_INCOMPLETE,
                        "Required MCP evidence retrieval was incomplete.",
                    )

                base_final_messages = build_final_decision_messages(
                    bridge.tool_history,
                    analysis_focus,
                )
                final_system_prompt = base_final_messages[0]["content"]
                final_prompt = base_final_messages[1]["content"]
                while True:
                    report(3, "Generating compact qwen3:4b advisory decision")
                    final_started = time.perf_counter()
                    try:
                        response = await self._chat(
                            base_final_messages,
                            [],
                            final_schema,
                        )
                    except AgentError as exc:
                        if exc.code != AgentErrorCode.LLM_TIMEOUT:
                            raise
                        fallback_used = True
                        proposal_source = "deterministic_timeout_fallback"
                        error_code = exc.code.value
                        error_message = exc.public_message
                        report(4, "Running deterministic validation")
                        validation_started = time.perf_counter()
                        try:
                            decision = build_timeout_fallback_decision(
                                bridge.tool_history
                            )
                            proposal = assemble_control_proposal(
                                decision,
                                bridge.tool_history,
                                self.settings,
                            )
                            validation = validate_proposal(
                                proposal,
                                bridge.tool_history,
                                self.settings,
                            )
                        finally:
                            validation_ms += (
                                time.perf_counter() - validation_started
                            ) * 1000
                        break
                    finally:
                        final_generation_ms += (
                            time.perf_counter() - final_started
                        ) * 1000
                    llm_completed = True
                    total_tokens["prompt"] += response.prompt_eval_count or 0
                    total_tokens["generation"] += response.eval_count or 0
                    final_text = response.raw_content

                    report(4, "Running deterministic validation")
                    validation_started = time.perf_counter()
                    errors: list[str] = []
                    try:
                        decision = LLMDecision.model_validate_json(final_text)
                        proposal = assemble_control_proposal(
                            decision,
                            bridge.tool_history,
                            self.settings,
                        )
                        validation = validate_proposal(
                            proposal,
                            bridge.tool_history,
                            self.settings,
                        )
                        errors = validation.validation_errors
                        proposal_source = "llm_decision"
                    except (ValidationError, ValueError) as exc:
                        errors = [
                            f"Structured LLM decision is invalid: {str(exc)[:1000]}"
                        ]
                        validation = ProposalValidationResult(
                            valid=False,
                            validation_errors=errors,
                            validation_warnings=[],
                            normalized_proposal=None,
                            validator_version=VALIDATOR_VERSION,
                        )
                    finally:
                        validation_ms += (
                            time.perf_counter() - validation_started
                        ) * 1000

                    if validation.valid:
                        break
                    if not can_retry(retry_count, self.settings.max_retries):
                        raise AgentError(
                            AgentErrorCode.MAX_RETRIES,
                            "Proposal remained invalid after bounded retries.",
                        )
                    retry_count += 1
                    correction = "; ".join(errors[:10])
                    base_final_messages = [
                        {
                            "role": "system",
                            "content": final_system_prompt,
                        },
                        {
                            "role": "user",
                            "content": (
                                f"{final_prompt}\nPrevious decision errors: "
                                f"{correction}. Return one corrected JSON object."
                            ),
                        }
                    ]
        except AgentError as exc:
            error_code, error_message = exc.code.value, exc.public_message
        except Exception as exc:
            error_code = AgentErrorCode.INTERNAL_ERROR.value
            error_message = f"Agent failed internally: {type(exc).__name__}."

        success = (
            validation is not None
            and validation.valid
            and (error_code is None or fallback_used)
        )
        official_used = any(
            event.get("response", {}).get("metadata", {}).get("classification")
            in {"official_energyplus_baseline", "energyplus_readiness"}
            for event in self.bridge.tool_history
        )
        total_mcp_ms = sum(
            float(event.get("duration_ms") or 0)
            for event in self.bridge.tool_history
        )
        run_work_ms = (time.perf_counter() - started) * 1000
        timing_fields = {
            "ollama_readiness_ms": readiness_ms,
            "initial_tool_selection_inference_ms": initial_inference_ms,
            "total_mcp_execution_ms": total_mcp_ms,
            "final_decision_generation_ms": final_generation_ms,
            "validation_ms": validation_ms,
            "total_run_ms": run_work_ms,
        }
        documents: dict[str, Any] = {
            "run_metadata.json": {
                "agent_run_id": run_id,
                "classification": "llm_advisory_proposal",
                "provider": self.settings.provider,
                "model": self.settings.model,
                "success": success,
                "retry_count": retry_count,
                "tool_rounds": tool_rounds,
                "context_characters": (
                    len(final_system_prompt) + len(final_prompt)
                ),
                "evidence_retrieval_mode": EVIDENCE_RETRIEVAL_MODE,
                "fallback_used": fallback_used,
                "llm_completed": llm_completed,
                "proposal_source": proposal_source,
                "final_prompt_characters": (
                    len(final_system_prompt) + len(final_prompt)
                ),
                "final_schema_characters": final_schema_characters,
                "generated_token_cap": self.settings.num_predict,
                **timing_fields,
                "official_energyplus_data_used": official_used,
                "advisory_only": True,
                "applied_to_energyplus": False,
                "closed_loop": False,
                "optimized_result": False,
                "savings_result": False,
            },
            "tool_calls.json": [
                {
                    key: event.get(key)
                    for key in (
                        "round",
                        "tool",
                        "arguments",
                        "duration_ms",
                        "success",
                    )
                }
                for event in self.bridge.tool_history
            ],
            "tool_result_summaries.json": [
                {
                    "tool": event.get("tool"),
                    "classification": event.get("response", {})
                    .get("metadata", {})
                    .get("classification"),
                    "record_count": event.get("response", {})
                    .get("metadata", {})
                    .get("record_count"),
                    "truncated": event.get("truncated"),
                }
                for event in self.bridge.tool_history
            ],
            "tool_responses.json": [
                {
                    "tool": event.get("tool"),
                    "response": event.get("response"),
                }
                for event in self.bridge.tool_history
            ],
            "validation.json": (
                validation.model_dump()
                if validation
                else {
                    "valid": False,
                    "validation_errors": [error_message or "No proposal."],
                    "validator_version": VALIDATOR_VERSION,
                }
            ),
            "final_response.txt": final_text,
            "prompt_metadata.json": {
                "prompt_version": PROMPT_VERSION,
                "system_prompt_sha256": hashlib.sha256(
                    final_system_prompt.encode()
                ).hexdigest(),
                "compact_system_prompt": final_system_prompt,
                "compact_evidence_prompt": final_prompt,
                "final_prompt_characters": (
                    len(final_system_prompt) + len(final_prompt)
                ),
                "schema": final_schema,
                "schema_characters": final_schema_characters,
                "generated_token_cap": self.settings.num_predict,
            },
        }
        if decision is not None:
            decision_name = (
                "fallback_decision.json"
                if fallback_used
                else "llm_decision.json"
            )
            documents[decision_name] = decision.model_dump()
        if proposal is not None:
            documents["proposal.json"] = proposal.model_dump()
        if error_code is not None:
            documents["error.json"] = {
                "code": error_code,
                "message": error_message,
            }
        try:
            artifact_directory = str(
                self.audit_writer.write_artifacts(run_id, documents)
            )
        except (OSError, ValueError, FileExistsError):
            if success:
                success = False
                error_code = AgentErrorCode.INTERNAL_ERROR.value
                error_message = "Agent artifacts could not be written."

        total_run_ms = (time.perf_counter() - started) * 1000
        self.audit_writer.append_audit(
            {
                "agent_run_id": run_id,
                "provider": self.settings.provider,
                "model": self.settings.model,
                "prompt_version": PROMPT_VERSION,
                "validator_version": VALIDATOR_VERSION,
                "mcp_server": "ecopilot-energyplus",
                "discovered_tool_count": len(
                    getattr(self.bridge, "tools_by_name", {})
                ),
                "exposed_tool_names": list(
                    getattr(self.bridge, "tools_by_name", {})
                ),
                "tool_call_sequence": [
                    event.get("tool") for event in self.bridge.tool_history
                ],
                "tool_duration_summaries": [
                    {
                        "tool": event.get("tool"),
                        "duration_ms": event.get("duration_ms"),
                    }
                    for event in self.bridge.tool_history
                ],
                "initial_tool_selection_inference_ms": initial_inference_ms,
                "ollama_readiness_ms": readiness_ms,
                "evidence_retrieval_mode": EVIDENCE_RETRIEVAL_MODE,
                "fallback_used": fallback_used,
                "llm_completed": llm_completed,
                "proposal_source": proposal_source,
                "total_mcp_execution_ms": total_mcp_ms,
                "final_decision_generation_ms": final_generation_ms,
                "validation_ms": validation_ms,
                "total_run_ms": total_run_ms,
                "token_counts": total_tokens,
                "retry_count": retry_count,
                "proposal_id": proposal.proposal_id if proposal else None,
                "validation_result": validation.valid if validation else False,
                "error_code": error_code,
                "artifact_path": artifact_directory,
                "final_status": (
                    "validated_timeout_fallback"
                    if fallback_used and success
                    else "success"
                    if success
                    else "failed"
                ),
            }
        )
        return AgentRunResult(
            success=success,
            agent_run_id=run_id,
            provider=self.settings.provider,
            model=self.settings.model,
            prompt_version=PROMPT_VERSION,
            proposal=proposal if success else None,
            validation=validation,
            tool_history=[
                {
                    key: event.get(key)
                    for key in (
                        "round",
                        "tool",
                        "arguments",
                        "duration_ms",
                        "success",
                    )
                }
                for event in self.bridge.tool_history
            ],
            retry_count=retry_count,
            context_characters=(
                len(final_system_prompt) + len(final_prompt)
            ),
            evidence_retrieval_mode=EVIDENCE_RETRIEVAL_MODE,
            proposal_source=proposal_source,
            fallback_used=fallback_used,
            llm_completed=llm_completed,
            final_prompt_characters=(
                len(final_system_prompt) + len(final_prompt)
            ),
            final_schema_characters=final_schema_characters,
            generated_token_cap=self.settings.num_predict,
            ollama_readiness_ms=readiness_ms,
            initial_tool_selection_inference_ms=initial_inference_ms,
            total_mcp_execution_ms=total_mcp_ms,
            final_decision_generation_ms=final_generation_ms,
            validation_ms=validation_ms,
            total_run_ms=total_run_ms,
            artifact_directory=artifact_directory,
            error_code=error_code,
            error_message=error_message,
            official_energyplus_data_used=official_used,
            completed_at=datetime.now(timezone.utc),
        )


__all__ = [
    "AdvisoryAgent",
    "EVIDENCE_RETRIEVAL_MODE",
    "REQUIRED_EVIDENCE_TOOLS",
]
