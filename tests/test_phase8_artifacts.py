from dataclasses import replace
from pathlib import Path

from energyplus.runtime_control.artifacts import (
    Phase8Artifacts,
    REQUIRED_ARTIFACTS,
)
from energyplus.runtime_control.settings import PHASE8_SETTINGS


def test_complete_artifact_bundle(tmp_path: Path):
    settings = replace(
        PHASE8_SETTINGS,
        repository_root=tmp_path,
        source_model_path=Path("model.idf"),
        runtime_model_path=Path("model.idf"),
        weather_file_path=Path("weather.epw"),
        artifact_root=Path("artifacts"),
        audit_path=Path("audit.jsonl"),
        official_inventory_path=Path("inventory.json"),
        output_root=Path("output"),
    )
    (tmp_path / "model.idf").write_text("Version,26.1;", encoding="utf-8")
    writer = Phase8Artifacts("mock", settings=settings)
    directory = writer.finalize(
        {"classification": "fixture", "success": False}
    )
    assert {item.name for item in directory.iterdir()} == set(REQUIRED_ARTIFACTS)
