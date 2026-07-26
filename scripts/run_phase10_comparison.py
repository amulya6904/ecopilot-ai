"""Create the official Phase 10 comparison from manifest-selected runs."""

import argparse
import json
from pathlib import Path

from comparison.runner import run_comparison


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline-artifact",
        type=Path,
        help="Optional explicit artifact path inside project results.",
    )
    parser.add_argument(
        "--controlled-artifact",
        type=Path,
        help="Optional explicit artifact path inside project results.",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    result = run_comparison(
        baseline_path=args.baseline_artifact,
        controlled_path=args.controlled_artifact,
    )
    print(json.dumps(result.summary, indent=2, default=str))
    print(f"Artifacts: {result.artifact_directory}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
