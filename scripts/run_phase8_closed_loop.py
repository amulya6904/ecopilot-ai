"""Opt-in Phase 7 advisory adapter; inference never occurs in a callback."""

import argparse
import asyncio
from dataclasses import replace
import json

from energyplus.runtime_control.action_provider import Phase7ProposalProvider
from energyplus.runtime_control.llm_adapter import (
    probe_live_runtime_context,
    request_runtime_llm_decision,
)
from energyplus.runtime_control.runtime_runner import run_phase8_runtime
from energyplus.runtime_control.settings import PHASE8_SETTINGS


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--enable-real-llm",
        action="store_true",
        help="Explicitly allow one Phase 7 advisory run before EnergyPlus starts.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if not args.enable_real_llm:
        print(
            "Real LLM mode is disabled. Re-run with --enable-real-llm "
            "after the mock closed-loop validation succeeds."
        )
        return 2
    settings = replace(PHASE8_SETTINGS, enable_real_llm=True)
    live_context = probe_live_runtime_context(settings)
    outcome = asyncio.run(request_runtime_llm_decision(live_context))
    runtime_result = run_phase8_runtime(
        Phase7ProposalProvider(
            outcome.decision,
            None,
            settings,
            live_context=live_context,
            llm_called=outcome.llm_called,
            llm_completed=outcome.llm_completed,
            llm_error_code=outcome.error_code,
            llm_error_message=outcome.error_message,
            llm_raw_content=outcome.raw_content,
            llm_messages=outcome.messages,
        ),
        mode="phase7_llm",
        classification="llm_assisted_energyplus_closed_loop_validation",
        real_llm_used=outcome.llm_called,
        settings=settings,
    )
    print(json.dumps(runtime_result.summary, indent=2, default=str))
    print(f"Artifacts: {runtime_result.artifact_directory}")
    return 0 if runtime_result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
