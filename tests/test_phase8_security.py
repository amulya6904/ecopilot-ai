from pathlib import Path

import pytest

from energyplus.runtime_control.settings import Phase8Settings


def test_runtime_model_cannot_escape_repository(tmp_path: Path):
    with pytest.raises(ValueError):
        Phase8Settings(
            repository_root=tmp_path,
            source_model_path=Path("ok.idf"),
            runtime_model_path=tmp_path.parent / "outside.idf",
            weather_file_path=Path("weather.epw"),
        )
