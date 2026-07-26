"""Deterministic Phase 7 smoke test, with an optional live Ollama mode."""

import argparse
import asyncio
from contextlib import asynccontextmanager
import json
from types import SimpleNamespace
from typing import Any

from llm.agent import AdvisoryAgent
from llm.mcp_client import MODEL_TOOL_ALLOWLIST
from llm.schemas import LLMClientResult, OllamaAvailability
from llm.settings import LLM_SETTINGS, LLMSettings


def valid_decision() -> dict[str, Any]:
    return {
        "energyplus_zone_name": "SPACE1-1",
        "proposed_setpoint_c": 23.0,
        "objective": "reduce_peak_demand",
        "confidence": 0.45,
        "reason": "A conservative one-degree advisory change is supported by official evidence.",
    }


def valid_proposal() -> dict[str, Any]:
    return {
        "proposal_id": "phase7-mock-proposal-001",
        "decision_type": "cooling_setpoint_advisory",
        "energyplus_zone_name": "SPACE1-1",
        "display_zone_name": "Open Office",
        "current_setpoint_c": 22.0,
        "proposed_setpoint_c": 23.0,
        "setpoint_change_c": 1.0,
        "effective_period": {
            "start_hour": 9, "end_hour": 18,
            "description": "Future occupied period; advisory only.",
        },
        "objective": "Evaluate a future opportunity to reduce cooling demand while preserving comfort.",
        "evidence": [
            {
                "source_tool": "get_official_baseline_summary",
                "metric": "total_facility_electricity_kwh", "value": 58568.0,
                "unit": "kWh", "observation": "Official fixed-schedule baseline total.",
            },
            {
                "source_tool": "get_facility_summary",
                "metric": "peak_facility_demand_kw", "value": 11.2,
                "unit": "kW", "observation": "Official baseline peak demand.",
            },
            {
                "source_tool": "get_thermostat_adherence",
                "metric": "current_cooling_setpoint_c", "value": 22.0,
                "unit": "degC", "observation": "Occupied cooling policy setpoint.",
            },
            {
                "source_tool": "get_comfort_summary",
                "metric": "temperature_compliance_percent", "value": 96.0,
                "unit": "percent", "observation": "Occupied temperature compliance.",
            },
        ],
        "comfort_assessment": {
            "occupancy_source": "energyplus_people_output",
            "temperature_compliance_percent": 96.0,
            "pmv_available": False, "pmv_compliance_percent": None,
            "risk_level": "medium",
            "limitations": ["PMV is unavailable; future matched simulation and safety review are required."],
        },
        "expected_effect": {
            "energy": "May reduce cooling energy; not quantified in Phase 7.",
            "comfort": "Could raise zone temperature and requires deterministic review.",
            "demand": "May reduce peak cooling demand; this has not been simulated.",
            "uncertainty": "No action was applied and no savings comparison was performed.",
        },
        "confidence": 0.45,
        "reason": "A conservative one-degree advisory change is within configured bounds and grounded in MCP evidence.",
        "advisory_only": True, "requires_safety_review": True,
        "applied_to_energyplus": False, "closed_loop": False,
        "optimized_result": False, "savings_result": False,
    }


def mock_tool_data(name: str) -> dict[str, Any]:
    data: dict[str, Any]
    if name == "list_zones":
        data = {"zones": [
            {
                "energyplus_zone_name": "SPACE1-1", "display_zone_name": "Open Office",
                "role": "primary_occupied", "included_in_comfort": True,
            },
            {
                "energyplus_zone_name": "PLENUM-1", "display_zone_name": "HVAC Plenum",
                "role": "plenum", "included_in_comfort": False,
            },
        ]}
    elif name == "get_comfort_summary":
        data = {
            "occupancy_source": "energyplus_people_output",
            "temperature_compliance_percent": 96.0, "pmv_available": False,
            "pmv_compliance_percent": None,
        }
    elif name == "get_thermostat_adherence":
        data = {"frozen_policy": {
            "heating_setpoint_c": {"occupied": 20.0},
            "cooling_setpoint_c": {"occupied": 22.0},
        }}
    elif name == "get_official_baseline_summary":
        data = {
            "total_facility_electricity_kwh": 58568.0,
            "classification": "official_energyplus_baseline",
        }
    elif name == "get_facility_summary":
        data = {"peak_facility_demand_kw": 11.2}
    else:
        data = {"available": True}
    return {
        "success": True, "data": data,
        "metadata": {
            "classification": "official_energyplus_baseline",
            "record_count": 1,
        },
    }


class MockBridge:
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self.tool_history: list[dict[str, Any]] = []
        self.tools_by_name = {
            name: SimpleNamespace(
                name=name, description=f"Read {name}.",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
            )
            for name in MODEL_TOOL_ALLOWLIST
        }

    @asynccontextmanager
    async def connect(self):
        yield self

    def ollama_tools(self):
        return [{
            "type": "function",
            "function": {
                "name": item.name, "description": item.description,
                "parameters": item.inputSchema,
            },
        } for item in self.tools_by_name.values()]

    async def call_tool(self, name: str, arguments: dict[str, Any], round_number: int):
        if name not in self.tools_by_name:
            raise RuntimeError("mock received a non-allowlisted tool")
        response = mock_tool_data(name)
        event = {
            "round": round_number, "tool": name, "arguments": arguments,
            "duration_ms": 0.1, "success": True, "response": response,
            "model_content": json.dumps(response), "truncated": False,
        }
        self.tool_history.append(event)
        return event


class MockLLMClient:
    def __init__(self, final: dict[str, Any] | None = None):
        self.calls = 0
        self.final = final or valid_decision()

    def discover(self):
        return OllamaAvailability(
            available=True, host="http://127.0.0.1:11434", version="mock",
            configured_model="mock-model", model_installed=True,
            installed_models=["mock-model"], reason=None, readiness_issues=[],
        )

    def chat(self, messages, tools, format_schema=None):
        self.calls += 1
        content = json.dumps(self.final)
        return LLMClientResult(
            model="mock-model", message={"role": "assistant", "content": content},
            tool_calls=[], raw_content=content, prompt_eval_count=200, eval_count=80,
        )


async def deterministic_smoke(settings: LLMSettings = LLM_SETTINGS):
    return await AdvisoryAgent(
        settings, llm_client=MockLLMClient(), bridge=MockBridge(settings)
    ).run()


async def _main(live: bool) -> int:
    result = await (AdvisoryAgent(LLM_SETTINGS).run() if live else deterministic_smoke())
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    if not result.success:
        return 1
    if result.applied_to_energyplus or not result.advisory_only:
        return 2
    print("Phase 7 agent smoke test passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Use local Ollama and the real Phase 6 MCP server.")
    return asyncio.run(_main(parser.parse_args().live))


if __name__ == "__main__":
    raise SystemExit(main())
