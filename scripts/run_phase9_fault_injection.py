"""Execute and persist all 22 deterministic Phase 9 fault scenarios."""

import json

from safety.artifacts import SafetyArtifacts
from safety.fault_injection import run_fault_injection_suite


def main() -> int:
    results = run_fault_injection_suite()
    artifacts = SafetyArtifacts("fault-injection")
    artifacts.fault_injection_results.extend(results)
    directory = artifacts.finalize()
    for item in results:
        print(
            f"{'PASS' if item['passed'] else 'FAIL'} "
            f"{item['scenario']}: {item['actual_outcome']} "
            f"[{item['expected_rule']}]"
        )
    passed = sum(bool(item["passed"]) for item in results)
    print(
        json.dumps(
            {
                "passed": passed,
                "total": len(results),
                "artifact_directory": str(directory),
            },
            indent=2,
        )
    )
    return 0 if passed == len(results) == 22 else 1


if __name__ == "__main__":
    raise SystemExit(main())
