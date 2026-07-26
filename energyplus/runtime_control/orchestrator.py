"""High-level Phase 8 entry points used by scripts and Streamlit."""

from .action_provider import ManualActionProvider, MockActionProvider
from .runtime_runner import Phase8RunResult, run_phase8_runtime
from .settings import PHASE8_SETTINGS, Phase8Settings


def run_manual_validation(
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> Phase8RunResult:
    return run_phase8_runtime(
        ManualActionProvider(settings),
        mode="manual",
        classification="manual_energyplus_actuator_validation",
        settings=settings,
    )


def run_mock_closed_loop(
    settings: Phase8Settings = PHASE8_SETTINGS,
) -> Phase8RunResult:
    return run_phase8_runtime(
        MockActionProvider(settings),
        mode="mock",
        classification="mock_agent_energyplus_closed_loop_validation",
        settings=settings,
    )


__all__ = ["run_manual_validation", "run_mock_closed_loop"]
