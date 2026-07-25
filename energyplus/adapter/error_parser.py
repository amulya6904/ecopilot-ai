"""Parse EnergyPlus warnings and errors from ``eplusout.err``."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

from schemas import RuntimeErrorRecord


@dataclass(frozen=True)
class EnergyPlusErrorSummary:
    warning_count: int
    severe_count: int
    fatal_count: int
    records: tuple[RuntimeErrorRecord, ...]


def classify_energyplus_warning(message: str) -> str:
    """Classify a warning without suppressing it."""
    normalized = message.casefold()
    if "weather file location" in normalized and "location object" in normalized:
        return "weather_location_mismatch"
    if "sizing" in normalized:
        return "sizing_issue"
    if "unused" in normalized:
        return "unused_object"
    if "report" in normalized or "output" in normalized:
        return "reporting_issue"
    return "other"


_DIAGNOSTIC = re.compile(
    r"^\s*\*\*\s*(Warning|Severe|Fatal)\s*\*\*\s*(.*)$", re.IGNORECASE
)


def parse_energyplus_error_file(path: Path) -> EnergyPlusErrorSummary:
    """Parse primary diagnostics while preserving concise raw excerpts."""
    error_path = Path(path)
    if not error_path.is_file():
        return EnergyPlusErrorSummary(0, 0, 0, ())
    records: list[RuntimeErrorRecord] = []
    lines = error_path.read_text(encoding="utf-8", errors="replace").splitlines()
    index = 0
    while index < len(lines):
        match = _DIAGNOSTIC.match(lines[index])
        if not match:
            index += 1
            continue
        severity = match.group(1).lower()
        message_parts = [match.group(2).strip()]
        raw = [lines[index]]
        index += 1
        while index < len(lines) and lines[index].lstrip().startswith("**   ~~~   **"):
            raw.append(lines[index])
            message_parts.append(lines[index].split("**", 2)[-1].strip(" *~"))
            index += 1
        records.append(
            RuntimeErrorRecord(
                timestamp=datetime.now(timezone.utc),
                source="energyplus",
                severity=severity,
                code=f"ENERGYPLUS_{severity.upper()}",
                message=" ".join(part for part in message_parts if part),
                raw_log_excerpt="\n".join(raw)[:4000],
                recoverable=severity == "warning",
            )
        )
    return EnergyPlusErrorSummary(
        warning_count=sum(item.severity == "warning" for item in records),
        severe_count=sum(item.severity == "severe" for item in records),
        fatal_count=sum(item.severity == "fatal" for item in records),
        records=tuple(records),
    )
