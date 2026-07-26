"""Fail-closed actuator reset and fallback event creation."""

from datetime import datetime
from typing import Any
import uuid

from .schemas import FallbackEvent


def reset_to_baseline(
    exchange: Any,
    state: Any,
    actuator_handle: int,
    *,
    reason_code: str,
    simulation_timestamp: datetime,
    original_action_id: str | None = None,
    fallback_value_c: float | None = None,
) -> FallbackEvent:
    reset = False
    if actuator_handle != -1:
        exchange.reset_actuator(state, actuator_handle)
        reset = True
    return FallbackEvent(
        fallback_id=f"fallback-{uuid.uuid4().hex}",
        reason_code=reason_code,
        original_action_id=original_action_id,
        fallback_value_c=fallback_value_c,
        actuator_reset=reset,
        simulation_timestamp=simulation_timestamp,
    )


__all__ = ["reset_to_baseline"]
