"""Run the complete Phase 10 controlled EnergyPlus evaluation."""

import argparse
import json

from comparison.runner import run_controlled_evaluation


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("reproducible_policy", "llm_assisted"),
        default="reproducible_policy",
    )
    parser.add_argument(
        "--enable-real-llm",
        action="store_true",
        help="Explicitly permit the bounded Phase 7 coarse advisory.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    result = run_controlled_evaluation(
        mode=args.mode,
        enable_real_llm=args.enable_real_llm,
    )
    print(json.dumps(result.summary, indent=2, default=str))
    print(f"Artifacts: {result.artifact_directory}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
