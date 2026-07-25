"""Tests for Phase 1-3 retrofit configuration and repository alignment."""

import importlib
from pathlib import Path

from config.settings import (
    AGENT,
    COMFORT_EVALUATION,
    ENERGYPLUS,
    PEAK_DEMAND,
    AgentSettings,
    ComfortEvaluationSettings,
    EnergyPlusSettings,
    PeakDemandSettings,
)

ROOT = Path(__file__).parents[1]


def test_future_integration_settings_load_with_safe_defaults() -> None:
    assert isinstance(ENERGYPLUS, EnergyPlusSettings)
    assert isinstance(AGENT, AgentSettings)
    assert isinstance(COMFORT_EVALUATION, ComfortEvaluationSettings)
    assert isinstance(PEAK_DEMAND, PeakDemandSettings)
    assert ENERGYPLUS.enabled is False
    assert ENERGYPLUS.primary_backend == "energyplus"
    assert ENERGYPLUS.fallback_backend == "lightweight"
    assert AGENT.enabled is False
    assert AGENT.tool_calling_enabled is False
    assert AGENT.mcp_enabled is False


def test_pmv_and_peak_demand_limits_are_ordered() -> None:
    assert (
        COMFORT_EVALUATION.pmv_allowed_min
        <= COMFORT_EVALUATION.pmv_preferred_min
        < COMFORT_EVALUATION.pmv_preferred_max
        <= COMFORT_EVALUATION.pmv_allowed_max
    )
    assert (
        0
        < PEAK_DEMAND.warning_threshold_kw
        < PEAK_DEMAND.critical_threshold_kw
    )


def test_phase13_imports_need_no_energyplus_ollama_or_mcp_runtime() -> None:
    importlib.import_module("app")
    importlib.import_module("backends")
    importlib.import_module("controllers.baseline")


def test_required_documents_and_directories_exist() -> None:
    required = [
        "docs/SYSTEM_ARCHITECTURE.md",
        "docs/OFFICIAL_REQUIREMENTS_MAPPING.md",
        "docs/PHASE_STATUS.md",
        "energyplus/README.md",
        "energyplus/models/.gitkeep",
        "energyplus/models/modified/.gitkeep",
        "energyplus/weather/.gitkeep",
        "energyplus/output/.gitkeep",
        "energyplus/logs/.gitkeep",
        "results/development/.gitkeep",
        "results/official/.gitkeep",
    ]
    assert all((ROOT / path).exists() for path in required)
