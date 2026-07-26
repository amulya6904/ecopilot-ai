"""Bounded proposal correction prompts."""

from llm.prompts import DEFAULT_AGENT_TASK


def retry_prompt(errors: list[str], task: str = DEFAULT_AGENT_TASK) -> str:
    compact = "; ".join(errors[:20])
    return (
        "Your previous final JSON failed deterministic validation. "
        f"Errors: {compact}. Original task: {task}. "
        "Return only one object matching the required LLMDecision schema. "
        "Correct these errors without adding unsupported facts or new tool claims. "
        "/no_think"
    )


def can_retry(retry_count: int, maximum: int) -> bool:
    return retry_count < maximum


__all__ = ["can_retry", "retry_prompt"]
