"""Complete deterministic artifact bundle for a Phase 9 safety run."""

import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from typing import Any
import uuid

from .schemas import SafetyRunSummary
from .settings import SAFETY_SETTINGS, SafetySettings


REQUIRED_SAFETY_ARTIFACTS = (
    "run_metadata.json",
    "safety_config.json",
    "safety_state_snapshots.csv",
    "proposed_actions.json",
    "safety_rule_results.json",
    "safety_decisions.json",
    "clamped_actions.json",
    "rejected_actions.json",
    "rollback_events.json",
    "emergency_events.json",
    "post_action_verification.json",
    "fault_injection_results.json",
    "runtime_errors.json",
    "summary.json",
)


def new_safety_run_id(mode: str = "validation") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-phase9-{mode}-{uuid.uuid4().hex[:8]}"


class SafetyArtifacts:
    def __init__(
        self,
        mode: str,
        *,
        run_id: str | None = None,
        settings: SafetySettings = SAFETY_SETTINGS,
    ) -> None:
        self.settings = settings
        self.mode = mode
        self.run_id = run_id or new_safety_run_id(mode)
        self.directory = settings.resolve(settings.artifact_root) / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.states: list[dict[str, Any]] = []
        self.proposed_actions: list[dict[str, Any]] = []
        self.rule_results: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []
        self.clamped_actions: list[dict[str, Any]] = []
        self.rejected_actions: list[dict[str, Any]] = []
        self.rollback_events: list[dict[str, Any]] = []
        self.emergency_events: list[dict[str, Any]] = []
        self.post_action_verification: list[dict[str, Any]] = []
        self.fault_injection_results: list[dict[str, Any]] = []
        self.runtime_errors: list[dict[str, Any]] = []
        self.metadata = {
            "run_id": self.run_id,
            "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "classification": (
                "safety_supervised_energyplus_runtime_validation"
            ),
            "safety_supervisor_enabled": True,
            "deterministic_safety_authority": True,
            "final_optimization_result": False,
            "savings_result": False,
        }

    @staticmethod
    def _dumpable(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "__dataclass_fields__"):
            return asdict(value)
        return dict(value)

    def add(self, collection: str, value: Any) -> None:
        getattr(self, collection).append(self._dumpable(value))

    def add_decision(self, state: Any, candidate: Any, decision: Any) -> None:
        self.add("states", state)
        self.add("proposed_actions", candidate)
        self.add("decisions", decision)
        for rule in decision.all_rule_results:
            row = rule.model_dump(mode="json")
            row.update(
                {
                    "decision_id": decision.decision_id,
                    "action_id": decision.action_id,
                }
            )
            self.rule_results.append(row)
        if decision.decision == "approve_with_clamp":
            self.clamped_actions.append(
                {
                    "action_id": decision.action_id,
                    "requested_value_c": decision.requested_value_c,
                    "approved_value_c": decision.approved_value_c,
                    "rules": [
                        rule.rule_id
                        for rule in decision.violated_rules
                        if rule.action == "clamp"
                    ],
                    "reason": "Deterministic nearby-safe-value clamp.",
                }
            )
        elif decision.decision in {
            "reject",
            "fallback",
            "emergency_fallback",
        }:
            self.rejected_actions.append(
                {
                    "action_id": decision.action_id,
                    "decision": decision.decision,
                    "requested_value_c": decision.requested_value_c,
                    "rule_ids": [
                        rule.rule_id for rule in decision.violated_rules
                    ],
                }
            )

    def _write_json(self, name: str, value: Any) -> None:
        (self.directory / name).write_text(
            json.dumps(value, indent=2, default=str, allow_nan=False),
            encoding="utf-8",
        )

    def _write_csv(self, name: str, rows: list[dict[str, Any]]) -> None:
        path = self.directory / name
        fields = sorted({key for row in rows for key in row})
        with path.open("w", newline="", encoding="utf-8") as stream:
            if fields:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

    def build_summary(
        self,
        *,
        severe_count: int = 0,
        fatal_count: int = 0,
    ) -> SafetyRunSummary:
        decisions = [item["decision"] for item in self.decisions]
        proposals = len(decisions)
        interventions = sum(value != "approve" for value in decisions)
        post_count = len(self.post_action_verification)
        post_verified = sum(
            bool(item["verified_safe"])
            for item in self.post_action_verification
        )
        comfort_prevented = sum(
            any(
                code in {
                    "PMV_HOT_LIMIT",
                    "PMV_COLD_LIMIT",
                    "TEMPERATURE_PROXY_DIRECTION_RISK",
                    "COMFORT_LIMIT_BREACH",
                }
                for code in item.get("rule_ids", [])
            )
            for item in self.rejected_actions
        )
        comfort_prevented += sum(
            bool(item.get("passed"))
            and item.get("expected_rule")
            in {
                "PMV_HOT_LIMIT",
                "PMV_COLD_LIMIT",
                "TEMPERATURE_PROXY_DIRECTION_RISK",
                "COMFORT_LIMIT_BREACH",
            }
            and item.get("actual_outcome")
            in {
                "approve_with_clamp",
                "hold",
                "reject",
                "fallback",
                "emergency_fallback",
                "rollback",
            }
            for item in self.fault_injection_results
        )
        demand_prevented = sum(
            any(code.startswith("DEMAND_") for code in item.get("rule_ids", []))
            for item in self.rejected_actions
        )
        demand_prevented += sum(
            bool(item.get("passed"))
            and str(item.get("expected_rule", "")).startswith("DEMAND_")
            and item.get("actual_outcome")
            in {
                "approve_with_clamp",
                "hold",
                "reject",
                "fallback",
                "emergency_fallback",
                "rollback",
            }
            for item in self.fault_injection_results
        )
        return SafetyRunSummary(
            comfort_method=(
                self.decisions[-1]["comfort_method"]
                if self.decisions
                else "occupied_temperature_proxy"
            ),
            pmv_available=any(
                bool(item["pmv_available"]) for item in self.decisions
            ),
            proposals=proposals,
            approved=decisions.count("approve"),
            clamped=decisions.count("approve_with_clamp"),
            held=decisions.count("hold"),
            rejected=decisions.count("reject"),
            fallbacks=decisions.count("fallback"),
            rollbacks=len(self.rollback_events),
            emergency_fallbacks=decisions.count("emergency_fallback"),
            safety_intervention_rate=(
                interventions / proposals if proposals else 0.0
            ),
            actuator_verification_success_rate=(
                post_verified / post_count if post_count else 0.0
            ),
            comfort_violations_prevented=comfort_prevented,
            demand_violations_prevented=demand_prevented,
            stale_data_rejections=sum(
                item.get("rule_id") == "TELEMETRY_STALE"
                and not item.get("passed", True)
                for item in self.rule_results
            )
            + sum(
                bool(item.get("passed"))
                and item.get("expected_rule") == "TELEMETRY_STALE"
                for item in self.fault_injection_results
            ),
            oscillation_events=sum(
                item.get("rule_id") == "ACTION_OSCILLATION_DETECTED"
                and not item.get("passed", True)
                for item in self.rule_results
            )
            + sum(
                bool(item.get("passed"))
                and item.get("expected_rule")
                == "ACTION_OSCILLATION_DETECTED"
                for item in self.fault_injection_results
            ),
            severe_count=severe_count,
            fatal_count=fatal_count,
        )

    def finalize(
        self,
        summary: SafetyRunSummary | None = None,
    ):
        summary = summary or self.build_summary()
        self._write_json("run_metadata.json", self.metadata)
        self._write_json("safety_config.json", asdict(self.settings))
        self._write_csv("safety_state_snapshots.csv", self.states)
        self._write_json("proposed_actions.json", self.proposed_actions)
        self._write_json("safety_rule_results.json", self.rule_results)
        self._write_json("safety_decisions.json", self.decisions)
        self._write_json("clamped_actions.json", self.clamped_actions)
        self._write_json("rejected_actions.json", self.rejected_actions)
        self._write_json("rollback_events.json", self.rollback_events)
        self._write_json("emergency_events.json", self.emergency_events)
        self._write_json(
            "post_action_verification.json",
            self.post_action_verification,
        )
        self._write_json(
            "fault_injection_results.json",
            self.fault_injection_results,
        )
        self._write_json("runtime_errors.json", self.runtime_errors)
        self._write_json("summary.json", summary.model_dump(mode="json"))
        return self.directory


__all__ = [
    "REQUIRED_SAFETY_ARTIFACTS",
    "SafetyArtifacts",
    "new_safety_run_id",
]
