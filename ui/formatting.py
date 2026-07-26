"""Central display formatting without changing stored calculations."""

from pathlib import Path


def _number(value: object, decimals: int) -> str:
    if value is None:
        return "Unavailable"
    return f"{float(value):,.{decimals}f}"


def format_energy(value: object, *, compact: bool = False) -> str:
    return f"{_number(value, 3 if compact else 2)} kWh"


def format_percent(value: object, decimals: int = 2) -> str:
    return f"{_number(value, decimals)}%"


def format_demand(value: object) -> str:
    return f"{_number(value, 3)} kW"


def format_comfort(value: object) -> str:
    return format_percent(value, 2)


def format_cost(value: object, currency: str = "INR") -> str:
    return f"{currency} {_number(value, 2)}"


def format_carbon(value: object) -> str:
    return f"{_number(value, 2)} kg CO₂"


def format_change(value: object, unit: str, decimals: int = 3) -> str:
    return f"{_number(value, decimals)} {unit}"


def peak_change_label(
    absolute_reduction_kw: object,
    *,
    tolerance_kw: float,
) -> str:
    if absolute_reduction_kw is None:
        return "Unavailable"
    value = float(absolute_reduction_kw)
    if abs(value) <= tolerance_kw:
        return "Essentially unchanged"
    if value > 0:
        return f"{value:,.3f} kW lower"
    return f"{abs(value):,.3f} kW higher"


def project_relative(path: Path, project_root: Path) -> str:
    resolved = Path(path).resolve()
    root = Path(project_root).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return "Outside approved project scope"


__all__ = [
    "format_carbon",
    "format_change",
    "format_comfort",
    "format_cost",
    "format_demand",
    "format_energy",
    "format_percent",
    "peak_change_label",
    "project_relative",
]
