"""Phase 8-only adapter from live Runtime API context to a compact Qwen request."""

import asyncio
from dataclasses import dataclass
import json
from typing import Any
import uuid

from pydantic import ValidationError

from llm.client import OllamaClient
from llm.errors import AgentError, AgentErrorCode
from llm.schemas import LLMDecision
from llm.settings import LLM_SETTINGS, LLMSettings

from .actuator_discovery import (
    filter_actuators,
    select_cooling_setpoint_actuator,
)
from .api_loader import load_energyplus_api
from .handles import initialize_handle_registry
from .settings import PHASE8_SETTINGS, Phase8Settings
from .telemetry import read_runtime_telemetry
from .variable_discovery import request_runtime_variables


RUNTIME_LLM_SYSTEM_PROMPT = (
    "Return one advisory cooling-setpoint decision as JSON matching the supplied "
    "schema. The live Runtime API context is authoritative. Choose only the supplied "
    "zone, stay within the stated bounds and maximum delta, and do not claim control "
    "application, optimization, deployment, or savings."
)


@dataclass(frozen=True)
class LiveRuntimeContext:
    zone: str
    live_current_setpoint_c: float
    minimum_setpoint_c: float
    maximum_setpoint_c: float
    maximum_delta_c: float
    zone_temperature_c: float
    heating_setpoint_c: float | None
    occupancy: float | None
    outdoor_temperature_c: float | None
    comfort_evidence_sufficient: bool
    pmv_available: bool
    objective: str
    advisory_only: bool
    actuator_identifier: str


@dataclass(frozen=True)
class RuntimeLLMOutcome:
    llm_called: bool
    llm_completed: bool
    decision: LLMDecision | None
    error_code: str | None
    error_message: str | None
    raw_content: str
    messages: list[dict[str, str]]


def probe_live_runtime_context(
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> LiveRuntimeContext:
    """Read the first non-warmup live setpoint before making any LLM request."""
    api, availability = load_energyplus_api(settings)
    if api is None or not availability.available:
        raise RuntimeError(
            "EnergyPlus Python API unavailable: "
            + "; ".join(availability.readiness_issues)
        )
    captured: LiveRuntimeContext | None = None
    errors: list[str] = []
    state = api.state_manager.new_state()
    request_runtime_variables(api.exchange, state, settings)

    def capture(runtime_state: Any) -> None:
        nonlocal captured
        try:
            if captured is not None:
                return
            if not api.exchange.api_data_fully_ready(runtime_state):
                return
            inventory = filter_actuators(
                api.exchange.get_api_data(runtime_state)
            )
            actuator = select_cooling_setpoint_actuator(inventory, settings)
            registry = initialize_handle_registry(
                api.exchange, runtime_state, actuator, settings
            )
            if not registry.ready:
                raise RuntimeError(
                    "Required live context handles are invalid: "
                    + ", ".join(registry.required_invalid)
                )
            telemetry = read_runtime_telemetry(
                api.exchange, runtime_state, registry, settings
            )
            if telemetry.warmup_flag:
                return
            occupancy = telemetry.occupancy
            captured = LiveRuntimeContext(
                zone=settings.controlled_zone,
                live_current_setpoint_c=(
                    telemetry.current_cooling_setpoint_c
                ),
                minimum_setpoint_c=settings.minimum_cooling_setpoint_c,
                maximum_setpoint_c=settings.maximum_cooling_setpoint_c,
                maximum_delta_c=settings.maximum_setpoint_change_c,
                zone_temperature_c=telemetry.zone_temperature_c,
                heating_setpoint_c=telemetry.current_heating_setpoint_c,
                occupancy=occupancy,
                outdoor_temperature_c=telemetry.outdoor_temperature_c,
                comfort_evidence_sufficient=(
                    occupancy is not None and occupancy <= 0.0
                ),
                pmv_available=False,
                objective="reduce_energy",
                advisory_only=True,
                actuator_identifier=actuator.identifier,
            )
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            api.runtime.stop_simulation(runtime_state)

    api.runtime.callback_after_predictor_before_hvac_managers(state, capture)
    output = (
        settings.resolve(settings.output_root)
        / f"llm-context-{uuid.uuid4().hex[:8]}"
    )
    output.mkdir(parents=True, exist_ok=False)
    args = [
        "-d",
        str(output),
        "-w",
        str(settings.resolve(settings.weather_file_path)),
        str(settings.resolve(settings.runtime_model_path)),
    ]
    try:
        exit_code = int(api.runtime.run_energyplus(state, args))
    finally:
        api.state_manager.delete_state(state)
    if exit_code != 0 or captured is None or errors:
        raise RuntimeError(
            "Live Runtime API context probe failed: "
            + "; ".join(errors or [f"EnergyPlus exit code {exit_code}"])
        )
    return captured


def build_runtime_llm_messages(
    context: LiveRuntimeContext,
) -> list[dict[str, str]]:
    compact = {
        "zone": context.zone,
        "live_current_setpoint_c": context.live_current_setpoint_c,
        "minimum_setpoint_c": context.minimum_setpoint_c,
        "maximum_setpoint_c": context.maximum_setpoint_c,
        "maximum_delta_c": context.maximum_delta_c,
        "current_comfort_evidence": {
            "zone_temperature_c": context.zone_temperature_c,
            "heating_setpoint_c": context.heating_setpoint_c,
            "occupancy": context.occupancy,
            "outdoor_temperature_c": context.outdoor_temperature_c,
            "pmv_available": context.pmv_available,
            "evidence_sufficient_for_conservative_adjustment": (
                context.comfort_evidence_sufficient
            ),
        },
        "objective": context.objective,
        "advisory_only_constraints": {
            "advisory_only": True,
            "requires_deterministic_runtime_validation": True,
            "no_optimization_claim": True,
            "no_savings_claim": True,
        },
    }
    return [
        {"role": "system", "content": RUNTIME_LLM_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Return only the compact JSON decision.\n"
                + json.dumps(
                    compact,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            ),
        },
    ]


async def request_runtime_llm_decision(
    context: LiveRuntimeContext,
    llm_settings: LLMSettings = LLM_SETTINGS,
) -> RuntimeLLMOutcome:
    messages = build_runtime_llm_messages(context)
    client = OllamaClient(llm_settings)
    readiness = client.discover()
    if not readiness.available or not readiness.model_installed:
        code = (
            AgentErrorCode.MODEL_NOT_INSTALLED
            if readiness.available and not readiness.model_installed
            else AgentErrorCode.OLLAMA_UNAVAILABLE
        )
        return RuntimeLLMOutcome(
            llm_called=False,
            llm_completed=False,
            decision=None,
            error_code=code.value,
            error_message=readiness.reason or "Ollama is unavailable.",
            raw_content="",
            messages=messages,
        )
    raw = ""
    try:
        result = await asyncio.wait_for(
            client.chat_async(
                messages=messages,
                tools=[],
                format_schema=LLMDecision.model_json_schema(),
            ),
            timeout=llm_settings.agent_run_timeout_seconds,
        )
        raw = result.raw_content
        decision = LLMDecision.model_validate_json(raw)
        return RuntimeLLMOutcome(
            llm_called=True,
            llm_completed=True,
            decision=decision,
            error_code=None,
            error_message=None,
            raw_content=raw,
            messages=messages,
        )
    except TimeoutError:
        code = AgentErrorCode.AGENT_RUN_TIMEOUT
        message = "Phase 8 compact LLM request exceeded the outer timeout."
    except AgentError as exc:
        code = exc.code
        message = exc.public_message
    except (ValidationError, ValueError, TypeError) as exc:
        code = AgentErrorCode.LLM_INVALID_RESPONSE
        message = f"Malformed Phase 8 LLM decision: {type(exc).__name__}."
    return RuntimeLLMOutcome(
        llm_called=True,
        llm_completed=False,
        decision=None,
        error_code=code.value,
        error_message=message,
        raw_content=raw,
        messages=messages,
    )


__all__ = [
    "LiveRuntimeContext",
    "RUNTIME_LLM_SYSTEM_PROMPT",
    "RuntimeLLMOutcome",
    "build_runtime_llm_messages",
    "probe_live_runtime_context",
    "request_runtime_llm_decision",
]
