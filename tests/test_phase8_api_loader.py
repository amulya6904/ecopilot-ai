from pathlib import Path

from energyplus.runtime_control.api_loader import inspect_runtime_availability
from energyplus.runtime_control.settings import Phase8Settings


def test_missing_installation_fails_closed(tmp_path: Path):
    settings = Phase8Settings(
        repository_root=tmp_path,
        installation_root=tmp_path / "missing",
        source_model_path=Path("source.idf"),
        runtime_model_path=Path("source.idf"),
        weather_file_path=Path("weather.epw"),
    )
    result = inspect_runtime_availability(settings)
    assert not result.available
    assert result.readiness_issues
