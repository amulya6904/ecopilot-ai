"""Strict structured proposal, provider, and run schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EvidenceItem(StrictModel):
    source_tool: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: float | int | str | bool | None
    unit: str
    observation: str = Field(min_length=1)


class EffectivePeriod(StrictModel):
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=1, le=24)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def ordered(self) -> "EffectivePeriod":
        if self.start_hour >= self.end_hour:
            raise ValueError("effective period start must precede end")
        return self


class ComfortAssessment(StrictModel):
    occupancy_source: str = Field(min_length=1)
    temperature_compliance_percent: float = Field(ge=0, le=100)
    pmv_available: bool
    pmv_compliance_percent: float | None = Field(default=None, ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    limitations: list[str] = Field(min_length=1)


class ExpectedEffect(StrictModel):
    energy: str = Field(min_length=1)
    comfort: str = Field(min_length=1)
    demand: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)


class LLMDecision(StrictModel):
    """The only fields the local model is allowed to decide."""

    energyplus_zone_name: str = Field(min_length=1)
    proposed_setpoint_c: float
    objective: Literal[
        "reduce_energy",
        "reduce_peak_demand",
        "maintain_comfort",
    ]
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=240)


class ControlProposal(StrictModel):
    proposal_id: str = Field(min_length=1)
    decision_type: Literal[
        "cooling_setpoint_advisory",
        "hold_current_setpoint",
    ] = "cooling_setpoint_advisory"
    energyplus_zone_name: str = Field(min_length=1)
    display_zone_name: str = Field(min_length=1)
    current_setpoint_c: float
    proposed_setpoint_c: float
    setpoint_change_c: float
    effective_period: EffectivePeriod
    objective: str = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(min_length=1)
    comfort_assessment: ComfortAssessment
    expected_effect: ExpectedEffect
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)
    advisory_only: Literal[True] = True
    requires_safety_review: Literal[True] = True
    applied_to_energyplus: Literal[False] = False
    closed_loop: Literal[False] = False
    optimized_result: Literal[False] = False
    savings_result: Literal[False] = False

    @model_validator(mode="after")
    def delta_matches(self) -> "ControlProposal":
        if abs((self.proposed_setpoint_c - self.current_setpoint_c) - self.setpoint_change_c) > 1e-6:
            raise ValueError("setpoint_change_c must equal proposed minus current")
        return self


class ProposalValidationResult(StrictModel):
    valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]
    normalized_proposal: ControlProposal | None = None
    validator_version: str


class OllamaAvailability(StrictModel):
    available: bool
    host: str
    version: str | None
    configured_model: str
    model_installed: bool
    installed_models: list[str]
    reason: str | None
    readiness_issues: list[str]


class ToolCall(StrictModel):
    name: str
    arguments: dict[str, Any]


class LLMClientResult(StrictModel):
    model: str
    created_at: str | None = None
    message: dict[str, Any]
    tool_calls: list[ToolCall]
    raw_content: str
    prompt_eval_duration_ns: int | None = None
    generation_duration_ns: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    total_duration_ns: int | None = None


class AgentRunResult(StrictModel):
    success: bool
    agent_run_id: str
    classification: Literal["llm_advisory_proposal"] = "llm_advisory_proposal"
    provider: str
    model: str
    prompt_version: str
    proposal: ControlProposal | None
    validation: ProposalValidationResult | None
    tool_history: list[dict[str, Any]]
    retry_count: int
    context_characters: int
    evidence_retrieval_mode: Literal["deterministic_required_mcp_plan"]
    proposal_source: Literal[
        "llm_decision",
        "deterministic_timeout_fallback",
        "none",
    ]
    fallback_used: bool
    llm_completed: bool
    final_prompt_characters: int
    final_schema_characters: int
    generated_token_cap: int
    ollama_readiness_ms: float
    initial_tool_selection_inference_ms: float | None
    total_mcp_execution_ms: float
    final_decision_generation_ms: float
    validation_ms: float
    total_run_ms: float
    artifact_directory: str | None
    error_code: str | None
    error_message: str | None
    official_energyplus_data_used: bool
    advisory_only: Literal[True] = True
    requires_safety_review: Literal[True] = True
    applied_to_energyplus: Literal[False] = False
    closed_loop: Literal[False] = False
    optimized_result: Literal[False] = False
    savings_result: Literal[False] = False
    completed_at: datetime


__all__ = [
    "AgentRunResult", "ComfortAssessment", "ControlProposal", "EffectivePeriod",
    "EvidenceItem", "ExpectedEffect", "LLMClientResult", "LLMDecision", "OllamaAvailability",
    "ProposalValidationResult", "ToolCall",
]
