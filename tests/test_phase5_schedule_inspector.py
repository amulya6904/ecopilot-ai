from pathlib import Path

from energyplus.baseline.schedule_inspector import inspect_baseline_model


FIXTURE = Path(__file__).parent / "fixtures" / "energyplus" / "phase5_minimal.idf"


def test_schedule_and_load_inventory_is_structured() -> None:
    inspection = inspect_baseline_model(FIXTURE)
    types = {item.object_type.casefold() for item in inspection.schedules}
    assert "schedule:compact" in types
    assert "schedule:ruleset" in types
    assert "schedule:constant" in types
    assert inspection.cooling_schedule_names == ("OLD-COOLING",)
    assert inspection.heating_schedule_names == ("OLD-HEATING",)
    assert len(inspection.thermostat_references) == 1
    assert inspection.thermostat_references[0].referenced_zones == ("SPACE1-1",)
    assert len(inspection.occupancy_references) == 1
    assert inspection.occupancy_references[0].referenced_schedule == "OCCUPY-1"
    assert len(inspection.people_objects) == 1
    assert len(inspection.lights_objects) == 1
    assert len(inspection.electric_equipment_objects) == 1
    assert inspection.output_requests


def test_unknown_objects_and_baseline_numbers_do_not_trigger_replacement(
    tmp_path: Path,
) -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    path = tmp_path / "unknown.idf"
    path.write_text(text + "\nUnknown:Thing,Number-22,22,27;\n", encoding="utf-8")
    inspection = inspect_baseline_model(path)
    assert inspection.object_count > 0
    assert "Number-22" in path.read_text(encoding="utf-8")
