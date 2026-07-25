import json
from pathlib import Path
from types import SimpleNamespace

from config.settings import EnergyPlusSettings
from energyplus.adapter.discovery import EnergyPlusAvailability
import energyplus.adapter.runner as runner


def test_readvars_conversion_is_isolated_to_the_run_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    installation = tmp_path / "EnergyPlus"
    executable = installation / "energyplus.exe"
    readvars = installation / "PostProcess" / "ReadVarsESO.exe"
    idd = installation / "Energy+.idd"
    model = tmp_path / "model.idf"
    weather = tmp_path / "weather.epw"
    for path in (executable, readvars, idd, model, weather):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    settings = EnergyPlusSettings(
        enabled=True,
        installation_dir=installation,
        executable_path=executable,
        idd_path=idd,
        base_model_path=model,
        weather_file_path=weather,
        output_root=tmp_path / "output",
        metadata_root=tmp_path / "metadata",
        expand_objects=False,
        readvars=True,
    )
    availability = EnergyPlusAvailability(
        installed=True,
        available=True,
        ready_for_run=True,
        executable_found=True,
        executable_path=executable,
        installation_dir=installation,
        idd_path=idd,
        idd_found=True,
        detected_version="26.1.0",
        expected_version="26.1",
        version_compatible=True,
        model_exists=True,
        weather_exists=True,
        output_root_ready=True,
        reason=None,
        readiness_issues=(),
    )
    monkeypatch.setattr(runner, "discover_energyplus", lambda _: availability)
    calls: list[tuple[list[str], Path | None]] = []

    def fake_subprocess_run(command, **kwargs):
        cwd = kwargs.get("cwd")
        calls.append((command, cwd))
        if command[0] == str(executable):
            assert "--readvars" not in command
            output_dir = Path(command[command.index("--output-directory") + 1])
            (output_dir / "eplusout.err").write_text("", encoding="utf-8")
            (output_dir / "eplusout.eso").write_text("eso", encoding="utf-8")
            (output_dir / "eplusout.sql").write_text("sql", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="EnergyPlus", stderr="")

        assert command[0] == str(readvars.resolve())
        assert cwd is not None
        output_dir = Path(cwd)
        rvi_path = Path(command[1])
        assert rvi_path.parent == output_dir
        eso_path, csv_path = rvi_path.read_text(encoding="utf-8").splitlines()
        assert Path(eso_path) == (output_dir / "eplusout.eso").resolve()
        assert Path(csv_path) == (output_dir / "eplusout.csv").resolve()
        Path(csv_path).write_text("Date/Time\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="ReadVarsESO", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_subprocess_run)

    result = runner.run_energyplus(settings, run_id="isolated-run")

    assert result.success, result.failure_reason
    assert result.csv_output_path == result.output_dir / "eplusout.csv"
    assert result.csv_output_path.is_file()
    assert len(calls) == 2
    assert not model.with_suffix(".rvi").exists()
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["readvars_exit_code"] == 0
    assert metadata["readvars_command"][0] == str(readvars.resolve())
