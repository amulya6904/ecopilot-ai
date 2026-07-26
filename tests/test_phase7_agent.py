import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

from llm.agent import (
    AdvisoryAgent,
    EVIDENCE_RETRIEVAL_MODE,
    REQUIRED_EVIDENCE_TOOLS,
)
from llm.errors import AgentError, AgentErrorCode
from llm.schemas import LLMClientResult, LLMDecision
from llm.settings import LLM_SETTINGS
from scripts.test_phase7_agent import (
    MockBridge,
    MockLLMClient,
    valid_decision,
    valid_proposal,
)


def settings(tmp_path, **changes):
    return replace(LLM_SETTINGS, repository_root=tmp_path, **changes)


class SequenceClient(MockLLMClient):
    def __init__(self, contents):
        super().__init__()
        self.contents = iter(contents)

    def chat(self, messages, tools, format_schema=None):
        value = next(self.contents)
        content = value if isinstance(value, str) else json.dumps(value)
        return LLMClientResult(
            model="mock", message={"role": "assistant", "content": content},
            tool_calls=[], raw_content=content,
        )


def test_successful_tool_loop(tmp_path):
    config = settings(tmp_path)
    client = MockLLMClient()
    result = asyncio.run(AdvisoryAgent(
        config, client, MockBridge(config)
    ).run())
    assert result.success
    assert client.calls == 1
    assert result.initial_tool_selection_inference_ms is None
    assert result.evidence_retrieval_mode == EVIDENCE_RETRIEVAL_MODE
    assert [event["tool"] for event in result.tool_history] == [
        name for name, _ in REQUIRED_EVIDENCE_TOOLS
    ]
    assert len(result.tool_history) == 5
    assert result.advisory_only and not result.applied_to_energyplus
    assert result.proposal is not None
    assert result.proposal.display_zone_name == "Open Office"
    assert result.proposal.current_setpoint_c == 22.0
    assert result.proposal.setpoint_change_c == 1.0
    assert {
        item.source_tool for item in result.proposal.evidence
    } >= {
        "get_official_baseline_summary",
        "get_facility_summary",
        "list_zones",
        "get_comfort_summary",
        "get_thermostat_adherence",
    }
    assert result.proposal.advisory_only is True
    assert result.proposal.requires_safety_review is True
    assert result.proposal.applied_to_energyplus is False
    assert result.proposal.closed_loop is False
    assert result.proposal.optimized_result is False
    assert result.proposal.savings_result is False
    evidence = {
        (item.source_tool, item.metric): item.value
        for item in result.proposal.evidence
    }
    assert evidence[
        ("get_official_baseline_summary", "total_facility_electricity_kwh")
    ] == 58568.0
    assert evidence[
        ("get_facility_summary", "peak_facility_demand_kw")
    ] == 11.2
    assert evidence[
        ("get_comfort_summary", "temperature_compliance_percent")
    ] == 96.0


def test_missing_required_tool_fails_before_llm(tmp_path):
    config = settings(tmp_path)
    bridge = MockBridge(config)
    bridge.tools_by_name.pop("get_comfort_summary")
    client = MockLLMClient()
    result = asyncio.run(AdvisoryAgent(config, client, bridge).run())
    assert not result.success
    assert result.error_code == AgentErrorCode.MCP_REQUIRED_TOOL_MISSING.value
    assert client.calls == 0


def test_invalid_json_retries(tmp_path):
    config = settings(tmp_path)
    client = SequenceClient(["not-json", valid_decision()])
    result = asyncio.run(AdvisoryAgent(config, client, MockBridge(config)).run())
    assert result.success
    assert result.retry_count == 1


def test_two_proposal_retries_remain_available_for_deterministic_tests(tmp_path):
    config = settings(tmp_path, max_retries=2)
    client = SequenceClient(["not-json", "still-not-json", valid_decision()])
    result = asyncio.run(AdvisoryAgent(config, client, MockBridge(config)).run())
    assert result.success
    assert result.retry_count == 2


def test_progress_reports_real_agent_stages(tmp_path):
    config = settings(tmp_path)
    stages = []
    result = asyncio.run(AdvisoryAgent(
        config, MockLLMClient(), MockBridge(config)
    ).run(progress_callback=lambda stage, message: stages.append((stage, message))))
    assert result.success
    assert [stage for stage, _ in stages] == [1, 2, 3, 4]


def test_validation_failure_retries(tmp_path):
    config = settings(tmp_path)
    invalid = valid_decision()
    invalid["energyplus_zone_name"] = "UNKNOWN"
    client = SequenceClient([invalid, valid_decision()])
    result = asyncio.run(AdvisoryAgent(config, client, MockBridge(config)).run())
    assert result.success and result.retry_count == 1


def test_invalid_zone_is_rejected_without_correction(tmp_path):
    config = settings(tmp_path, max_retries=0)
    invalid = valid_decision()
    invalid["energyplus_zone_name"] = "UNKNOWN"
    result = asyncio.run(AdvisoryAgent(
        config,
        SequenceClient([invalid]),
        MockBridge(config),
    ).run())
    assert not result.success
    assert result.validation and not result.validation.valid


def test_out_of_bounds_setpoint_is_rejected(tmp_path):
    config = settings(tmp_path, max_retries=0)
    invalid = valid_decision()
    invalid["proposed_setpoint_c"] = 29.0
    result = asyncio.run(AdvisoryAgent(
        config,
        SequenceClient([invalid]),
        MockBridge(config),
    ).run())
    assert not result.success
    assert result.validation and not result.validation.valid
    assert any("bounds" in error for error in result.validation.validation_errors)


def test_model_cannot_override_fixed_safety_flags(tmp_path):
    config = settings(tmp_path, max_retries=0)
    invalid = valid_decision()
    invalid.update({
        "advisory_only": False,
        "applied_to_energyplus": True,
    })
    result = asyncio.run(AdvisoryAgent(
        config,
        SequenceClient([invalid]),
        MockBridge(config),
    ).run())
    assert not result.success
    assert result.proposal is None
    assert result.validation and not result.validation.valid


def test_final_request_is_minimal_and_compact(tmp_path):
    config = settings(tmp_path)

    class RecordingClient(MockLLMClient):
        def __init__(self):
            super().__init__()
            self.requests = []

        def chat(self, messages, tools, format_schema=None):
            self.requests.append((messages, tools, format_schema))
            return super().chat(messages, tools, format_schema)

    client = RecordingClient()
    result = asyncio.run(AdvisoryAgent(
        config, client, MockBridge(config)
    ).run(analysis_focus="Prioritize peak demand."))
    assert result.success
    messages, tools, schema = client.requests[-1]
    assert tools == []
    assert len(messages) == 2
    assert [message["role"] for message in messages] == ["system", "user"]
    assert sum(len(message["content"]) for message in messages) == (
        result.final_prompt_characters
    )
    assert result.final_prompt_characters < 1_500
    assert "Prioritize peak demand." in messages[1]["content"]
    assert "boundary_samples" not in messages[1]["content"]
    assert "telemetry" not in messages[1]["content"]
    assert set(schema["properties"]) == set(
        LLMDecision.model_json_schema()["properties"]
    )
    assert "proposal_id" not in schema["properties"]
    assert "evidence" not in schema["properties"]


def test_llm_timeout_uses_separately_classified_fallback(tmp_path):
    config = settings(tmp_path)

    class TimeoutClient(MockLLMClient):
        def chat(self, messages, tools, format_schema=None):
            raise AgentError(AgentErrorCode.LLM_TIMEOUT, "timed out")

    result = asyncio.run(AdvisoryAgent(config, TimeoutClient(), MockBridge(config)).run())
    assert result.success
    assert result.error_code == AgentErrorCode.LLM_TIMEOUT.value
    assert len(result.tool_history) == 5
    assert all(event["success"] for event in result.tool_history)
    assert result.official_energyplus_data_used is True
    assert result.proposal is not None
    assert result.proposal.proposed_setpoint_c == 22.5
    assert result.proposal.setpoint_change_c == 0.5
    assert result.validation and result.validation.valid
    assert result.fallback_used is True
    assert result.llm_completed is False
    assert result.proposal_source == "deterministic_timeout_fallback"


def test_tool_failure_is_reported(tmp_path):
    config = settings(tmp_path)

    class FailedBridge(MockBridge):
        async def call_tool(self, name, arguments, round_number):
            if name == "list_zones":
                raise AgentError(AgentErrorCode.TOOL_CALL_FAILED, "failed")
            return await super().call_tool(name, arguments, round_number)

    client = MockLLMClient()
    result = asyncio.run(AdvisoryAgent(
        config, client, FailedBridge(config)
    ).run())
    assert result.error_code == AgentErrorCode.MCP_EVIDENCE_RETRIEVAL_FAILED.value
    assert [event["tool"] for event in result.tool_history] == [
        "get_official_baseline_summary",
        "get_facility_summary",
    ]
    assert client.calls == 0


def test_output_contains_no_unsupported_result_claims(tmp_path):
    config = settings(tmp_path)
    result = asyncio.run(AdvisoryAgent(config, MockLLMClient(), MockBridge(config)).run())
    assert result.proposal is not None
    assert not result.proposal.closed_loop
    assert not result.proposal.optimized_result
    assert not result.proposal.savings_result


def test_live_streamlit_path_does_not_use_mock_client():
    source = Path("ui/phase7.py").read_text(encoding="utf-8")
    assert "MockLLMClient" not in source
    assert "AdvisoryAgent(LLM_SETTINGS)" in source
