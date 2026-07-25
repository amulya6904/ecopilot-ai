"""Structured runtime failures for future tool and agent consumption."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RuntimeErrorRecord:
    """A normalized backend error with a bounded relevant log excerpt."""

    timestamp: datetime
    source: str
    severity: str
    code: str
    message: str
    raw_log_excerpt: str | None
    recoverable: bool

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime.")
        required = (self.source, self.severity, self.code, self.message)
        if any(not value.strip() for value in required):
            raise ValueError("source, severity, code, and message are required.")
