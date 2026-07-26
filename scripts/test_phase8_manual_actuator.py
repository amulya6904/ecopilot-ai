"""Prove a bounded 23 C Runtime API override and baseline reset."""

import json

from energyplus.runtime_control.orchestrator import run_manual_validation


def main() -> int:
    result = run_manual_validation()
    print(json.dumps(result.summary, indent=2, default=str))
    print(f"Artifacts: {result.artifact_directory}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
