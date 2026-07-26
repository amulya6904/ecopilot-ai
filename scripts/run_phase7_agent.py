"""Run the real local Phase 7 advisory workflow."""

import asyncio
import json

from llm.agent import AdvisoryAgent
from llm.settings import LLM_SETTINGS


async def _run() -> int:
    result = await AdvisoryAgent(LLM_SETTINGS).run()
    print("MCP tools called:", ", ".join(item["tool"] for item in result.tool_history) or "none")
    print("Proposal:")
    print(json.dumps(result.proposal.model_dump(mode="json") if result.proposal else None, indent=2))
    print("Validation:")
    print(json.dumps(result.validation.model_dump(mode="json") if result.validation else None, indent=2))
    print("Retry count:", result.retry_count)
    print("Advisory only:", result.advisory_only)
    print("Applied to EnergyPlus:", result.applied_to_energyplus)
    print("Artifact directory:", result.artifact_directory)
    if not result.success:
        print(f"Failure: {result.error_code}: {result.error_message}")
    return 0 if result.success else 1


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
