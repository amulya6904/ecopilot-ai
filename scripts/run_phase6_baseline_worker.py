"""Isolated main-process host for the existing Phase 5 baseline callable."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from energyplus.baseline.reproducibility import compare_baseline_runs
from energyplus.baseline.runner import run_energyplus_baseline
from energyplus.baseline.settings import ENERGYPLUS_BASELINE
from mcp_service.serialization import to_json_safe


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-reproducibility", action="store_true")
    parser.add_argument("--force-rebuild", action="store_true")
    return parser.parse_args()


def _artifacts(result) -> dict[str, str]:
    root = Path(__file__).parents[1].resolve()
    values = {}
    for name, path in result.artifact_paths.items():
        resolved = Path(path).resolve()
        values[name] = (
            str(resolved.relative_to(root))
            if root in resolved.parents else resolved.name
        )
    return values


def main() -> int:
    args = _arguments()
    first = run_energyplus_baseline(
        ENERGYPLUS_BASELINE,
        rebuild_model=args.force_rebuild,
    )
    if not first.success:
        print(json.dumps({
            "success": False,
            "failure_reason": first.failure_reason or "Official baseline execution failed.",
        }))
        return 1
    reproducibility = None
    if args.verify_reproducibility:
        second = run_energyplus_baseline(ENERGYPLUS_BASELINE, rebuild_model=True)
        if not second.success:
            print(json.dumps({
                "success": False,
                "failure_reason": second.failure_reason or "Reproducibility run failed.",
            }))
            return 1
        reproducibility = asdict(compare_baseline_runs(
            first, second, ENERGYPLUS_BASELINE.reproducibility_tolerance
        ))
    summary_keys = (
        "run_id", "classification", "official_result", "baseline_result",
        "total_facility_electricity_kwh", "peak_facility_demand_kw",
        "thermostat_adherence_percent", "warning_count", "severe_count",
        "fatal_count",
    )
    print(json.dumps(to_json_safe({
        "success": True,
        "summary": {
            key: first.baseline_summary.get(key) for key in summary_keys
        },
        "artifacts": _artifacts(first),
        "reproducibility": reproducibility,
        "control_modification": False,
        "lightweight_fallback": False,
    }), sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
