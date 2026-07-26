"""Bounded live Ollama test for compact final-decision generation only."""

import asyncio
import json
import time

from llm.client import OllamaClient
from llm.decision import (
    assemble_control_proposal,
    build_final_decision_messages,
)
from llm.schemas import LLMDecision
from llm.settings import LLM_SETTINGS
from llm.validator import validate_proposal
from scripts.test_phase7_agent import mock_tool_data


def supplied_official_history() -> list[dict]:
    return [
        {
            "round": 1,
            "tool": name,
            "arguments": {},
            "duration_ms": 0.0,
            "success": True,
            "response": mock_tool_data(name),
            "truncated": False,
        }
        for name in (
            "get_official_baseline_summary",
            "get_facility_summary",
            "list_zones",
            "get_comfort_summary",
            "get_thermostat_adherence",
        )
    ]


async def run_live_decision() -> dict:
    history = supplied_official_history()
    base_messages = build_final_decision_messages(history)
    prompt = base_messages[1]["content"]
    schema = LLMDecision.model_json_schema()
    schema_characters = len(
        json.dumps(schema, sort_keys=True, separators=(",", ":"))
    )
    client = OllamaClient(LLM_SETTINGS)
    readiness = await asyncio.to_thread(client.discover)
    if not readiness.available or not readiness.model_installed:
        raise RuntimeError(
            readiness.reason
            or f"Configured model {LLM_SETTINGS.model!r} is not ready."
        )
    started = time.perf_counter()
    messages = base_messages
    retry_count = 0
    while True:
        response = await client.chat_async(messages, [], schema)
        try:
            decision = LLMDecision.model_validate_json(response.raw_content)
            proposal = assemble_control_proposal(decision, history, LLM_SETTINGS)
            validation = validate_proposal(proposal, history, LLM_SETTINGS)
            if validation.valid:
                break
            error = "; ".join(validation.validation_errors)
        except Exception as exc:
            error = str(exc)
        if retry_count >= LLM_SETTINGS.max_retries:
            raise RuntimeError(f"Live decision remained invalid: {error}")
        retry_count += 1
        messages = [{
            "role": "system",
            "content": base_messages[0]["content"],
        }, {
            "role": "user",
            "content": (
                f"{prompt}\nPrevious decision error: {error[:800]}. "
                "Return one corrected JSON object."
            ),
        }]
    generation_ms = (time.perf_counter() - started) * 1000
    return {
        "success": validation.valid,
        "model": response.model,
        "final_prompt_characters": sum(
            len(message["content"]) for message in base_messages
        ),
        "final_schema_characters": schema_characters,
        "generated_token_cap": LLM_SETTINGS.num_predict,
        "final_decision_generation_ms": generation_ms,
        "validator_accepted": validation.valid,
        "validation_errors": validation.validation_errors,
        "retry_count": retry_count,
        "decision": decision.model_dump(),
        "proposal_id": proposal.proposal_id,
    }


def main() -> int:
    started = time.perf_counter()
    try:
        result = asyncio.run(asyncio.wait_for(
            run_live_decision(),
            timeout=LLM_SETTINGS.final_request_timeout_seconds,
        ))
    except Exception as exc:
        result = {
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    result["total_live_duration_ms"] = (time.perf_counter() - started) * 1000
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
