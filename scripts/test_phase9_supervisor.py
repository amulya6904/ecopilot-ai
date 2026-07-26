"""Fast deterministic smoke test for every Phase 9 decision outcome."""

from safety.fault_injection import make_candidate, make_state
from safety.schemas import SafetyHistory, SafetyHistoryEntry
from safety.supervisor import evaluate_action_safety


def main() -> int:
    cases = [
        ("approve", make_state(), make_candidate(), SafetyHistory()),
        (
            "approve_with_clamp",
            make_state(),
            make_candidate(requested=29.0),
            SafetyHistory(),
        ),
        (
            "hold",
            make_state(warmup=True),
            make_candidate(),
            SafetyHistory(),
        ),
        (
            "reject",
            make_state(),
            make_candidate(
                requested=21.0,
                objective="reduce_energy",
            ),
            SafetyHistory(),
        ),
        (
            "fallback",
            make_state(telemetry_age_seconds=301.0),
            make_candidate(),
            SafetyHistory(),
        ),
        (
            "emergency_fallback",
            make_state(severe_runtime_error=True),
            make_candidate(),
            SafetyHistory(),
        ),
    ]
    failures = 0
    for expected, state, candidate, history in cases:
        decision = evaluate_action_safety(
            state, candidate, history=history
        )
        passed = decision.decision == expected
        failures += int(not passed)
        print(
            f"{'PASS' if passed else 'FAIL'} "
            f"{expected}: {decision.decision}"
        )
    print(f"Phase 9 supervisor: {len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
