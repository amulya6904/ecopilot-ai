"""Run the five-interval deterministic Phase 8 closed-loop proof."""

import json

from energyplus.runtime_control.orchestrator import run_mock_closed_loop


def main() -> int:
    result = run_mock_closed_loop()
    print(json.dumps(result.summary, indent=2, default=str))
    print(f"Artifacts: {result.artifact_directory}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
