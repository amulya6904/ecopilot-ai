import asyncio
from dataclasses import replace

import pytest

from llm.agent import AdvisoryAgent
from llm.client import OllamaClient
from llm.settings import LLM_SETTINGS


@pytest.mark.ollama
def test_live_ollama_mcp_advisory_agent():
    readiness = OllamaClient(LLM_SETTINGS).discover()
    if not readiness.available:
        pytest.skip(
            f"Local Ollama is unavailable at {readiness.host}: "
            f"{'; '.join(readiness.readiness_issues)}"
        )
    if not readiness.model_installed:
        pytest.skip(
            f"Configured model {readiness.configured_model!r} is not installed. "
            f"Installed models: {readiness.installed_models}. "
            f"Review model size, then run `ollama pull {readiness.configured_model}`."
        )
    result = asyncio.run(AdvisoryAgent(LLM_SETTINGS).run())
    assert result.success
    assert result.tool_history
    assert result.official_energyplus_data_used
    assert result.proposal is not None
    assert result.validation and result.validation.valid
    assert result.advisory_only
    assert not result.applied_to_energyplus
    assert result.artifact_directory
