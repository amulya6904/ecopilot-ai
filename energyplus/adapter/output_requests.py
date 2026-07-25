"""Create a derived IDF containing only Phase 4 telemetry additions."""

from pathlib import Path
import re


_HEADER = """\

! ================================================================
! EcoPilot AI Phase 4 telemetry additions
! Derived from energyplus/models/base/phase4_base_model.idf.
! The source model is preserved unchanged.
! ================================================================
"""

_REQUESTS = (
    (
        "zone_mean_air_temperature",
        "Output:Variable,\n"
        "    *,\n"
        "    Zone Mean Air Temperature,\n"
        "    Hourly;\n",
        r"Output:Variable\s*,\s*\*\s*,\s*Zone Mean Air Temperature\s*,\s*Hourly\s*;",
    ),
    (
        "outdoor_drybulb",
        "Output:Variable,\n"
        "    Environment,\n"
        "    Site Outdoor Air Drybulb Temperature,\n"
        "    Hourly;\n",
        r"Output:Variable\s*,\s*(?:Environment|\*)\s*,\s*"
        r"Site Outdoor Air Drybulb Temperature\s*,\s*Hourly\s*;",
    ),
    (
        "facility_demand",
        "Output:Variable,\n"
        "    Whole Building,\n"
        "    Facility Total Electricity Demand Rate,\n"
        "    Hourly;\n",
        r"Output:Variable\s*,\s*(?:Whole Building|\*)\s*,\s*"
        r"Facility Total Electricity Demand Rate\s*,\s*Hourly\s*;",
    ),
    (
        "facility_electricity",
        "Output:Meter,\n"
        "    Electricity:Facility,\n"
        "    Hourly;\n",
        r"Output:Meter\s*,\s*Electricity:Facility\s*,\s*Hourly\s*;",
    ),
    (
        "hvac_electricity",
        "Output:Meter,\n"
        "    Electricity:HVAC,\n"
        "    Hourly;\n",
        r"Output:Meter\s*,\s*Electricity:HVAC\s*,\s*Hourly\s*;",
    ),
    (
        "sqlite",
        "Output:SQLite,\n"
        "    SimpleAndTabular;\n",
        r"Output:SQLite\s*,",
    ),
)


def inspect_output_requests(model_path: Path) -> dict[str, bool]:
    """Return which exact Phase 4 requests are already present."""
    text = Path(model_path).read_text(encoding="utf-8", errors="replace")
    return {
        name: re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None
        for name, _, pattern in _REQUESTS
    }


def ensure_phase4_output_requests(
    source_model_path: Path,
    destination_model_path: Path,
) -> Path:
    """Write a derived telemetry IDF without changing the source IDF."""
    source = Path(source_model_path).resolve()
    destination = Path(destination_model_path).resolve()
    models_root = (Path(__file__).parents[1] / "models").resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Base EnergyPlus IDF does not exist: {source}")
    if destination == source:
        raise ValueError("Derived IDF destination must differ from the base IDF.")
    if destination != models_root and models_root not in destination.parents:
        raise ValueError("Derived IDF must be written under energyplus/models.")
    base_text = source.read_text(encoding="utf-8", errors="replace")
    additions = [_HEADER]
    for _, object_text, pattern in _REQUESTS:
        if re.search(pattern, base_text, re.IGNORECASE | re.DOTALL) is None:
            additions.append("\n" + object_text)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(base_text.rstrip() + "\n" + "".join(additions), encoding="utf-8")
    return destination
