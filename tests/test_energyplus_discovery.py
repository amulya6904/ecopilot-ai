from pathlib import Path
import subprocess

from config.settings import EnergyPlusSettings
from energyplus.adapter import discovery


def _settings(tmp_path: Path, *, executable: Path | None = None) -> EnergyPlusSettings:
    model = tmp_path / "model.idf"
    weather = tmp_path / "weather.epw"
    idd = tmp_path / "Energy+.idd"
    for path in (model, weather, idd):
        path.write_text("fixture", encoding="utf-8")
    return EnergyPlusSettings(
        executable_path=executable or tmp_path / "missing.exe",
        installation_dir=tmp_path,
        idd_path=idd,
        base_model_path=model,
        weather_file_path=weather,
        output_root=tmp_path / "output",
        logs_root=tmp_path / "logs",
        metadata_root=tmp_path / "metadata",
        expected_version=None,
    )


def test_missing_executable_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        discovery,
        "_candidate_executables",
        lambda settings: [tmp_path / "missing.exe"],
    )
    status = discovery.discover_energyplus(_settings(tmp_path))
    assert not status.available
    assert not status.executable_found
    assert "executable" in status.reason.lower()


def test_explicit_executable_and_version_are_detected(
    tmp_path: Path, monkeypatch
) -> None:
    executable = tmp_path / "energyplus.exe"
    executable.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        discovery.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "EnergyPlus, Version 26.1.0-6f2e40d102", ""
        ),
    )
    status = discovery.discover_energyplus(_settings(tmp_path, executable=executable))
    assert status.available
    assert status.executable_path == executable.resolve()
    assert status.detected_version == "26.1.0"
    assert status.installed and status.idd_found


def test_environment_executable_is_bounded_and_supported(
    tmp_path: Path, monkeypatch
) -> None:
    executable = tmp_path / "env-energyplus.exe"
    executable.write_text("", encoding="utf-8")
    settings = _settings(tmp_path)
    settings = EnergyPlusSettings(
        executable_path=Path("."),
        installation_dir=settings.installation_dir,
        idd_path=settings.idd_path,
        base_model_path=settings.base_model_path,
        weather_file_path=settings.weather_file_path,
        output_root=settings.output_root,
        logs_root=settings.logs_root,
        metadata_root=settings.metadata_root,
    )
    monkeypatch.setenv("ENERGYPLUS_EXECUTABLE", str(executable))
    monkeypatch.setattr(discovery, "get_energyplus_version", lambda path: "26.1.0")
    assert discovery.discover_energyplus(settings).executable_path == executable.resolve()


def test_version_timeout_and_nonzero_return_none(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "energyplus.exe"
    monkeypatch.setattr(
        discovery.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(args[0], 1)
        ),
    )
    assert discovery.get_energyplus_version(executable, 1) is None
    monkeypatch.setattr(
        discovery.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "failed"),
    )
    assert discovery.get_energyplus_version(executable) is None


def test_missing_model_and_weather_are_reported(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "energyplus.exe"
    executable.write_text("", encoding="utf-8")
    settings = _settings(tmp_path, executable=executable)
    settings.base_model_path.unlink()
    settings.weather_file_path.unlink()
    monkeypatch.setattr(discovery, "get_energyplus_version", lambda path: "26.1.0")
    status = discovery.discover_energyplus(settings)
    assert not status.model_exists and not status.weather_exists
    assert status.installed and not status.ready_for_run and not status.available
    assert any("IDF" in issue for issue in status.readiness_issues)
    assert any("EPW" in issue for issue in status.readiness_issues)


def test_default_paths_derive_from_energyplus_home(monkeypatch) -> None:
    monkeypatch.setenv("ENERGYPLUS_HOME", r"D:\EnergyPlus-Test")
    monkeypatch.delenv("ENERGYPLUS_EXECUTABLE", raising=False)
    monkeypatch.delenv("ENERGYPLUS_IDD", raising=False)
    settings = EnergyPlusSettings()
    assert settings.installation_dir == Path(r"D:\EnergyPlus-Test")
    assert settings.executable_path == Path(r"D:\EnergyPlus-Test\energyplus.exe")
    assert settings.idd_path == Path(r"D:\EnergyPlus-Test\Energy+.idd")
