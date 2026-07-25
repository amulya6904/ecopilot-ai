import importlib
from pathlib import Path
import subprocess
import sys


def test_phase5_modules_import_without_running_energyplus() -> None:
    for module in (
        "config.settings",
        "energyplus.baseline.settings",
        "energyplus.baseline.schedule_inspector",
        "energyplus.baseline.model_builder",
        "energyplus.baseline.normalizer",
        "energyplus.baseline.metrics",
        "energyplus.baseline.artifacts",
        "energyplus.baseline.manifest",
        "energyplus.baseline.reproducibility",
        "energyplus.baseline.runner",
        "scripts.run_phase5_energyplus_baseline",
        "ui.phase5",
        "app",
    ):
        importlib.import_module(module)


def test_phase5_settings_have_one_authoritative_definition_and_singleton() -> None:
    config = importlib.import_module("config.settings")
    settings = importlib.import_module("energyplus.baseline.settings")
    runner = importlib.import_module("energyplus.baseline.runner")
    phase5_ui = importlib.import_module("ui.phase5")
    script = importlib.import_module("scripts.run_phase5_energyplus_baseline")
    assert settings.EnergyPlusBaselineSettings.__module__ == (
        "energyplus.baseline.settings"
    )
    assert not hasattr(config, "EnergyPlusBaselineSettings")
    assert not hasattr(config, "ENERGYPLUS_BASELINE")
    assert runner.ENERGYPLUS_BASELINE is settings.ENERGYPLUS_BASELINE
    assert phase5_ui.ENERGYPLUS_BASELINE is settings.ENERGYPLUS_BASELINE
    assert script.ENERGYPLUS_BASELINE is settings.ENERGYPLUS_BASELINE


def test_fresh_import_process_does_not_write_or_execute_baseline() -> None:
    root = Path(__file__).parents[1]
    artifact = (
        root / "results/official/phase5_energyplus_baseline_summary.json"
    )
    before = artifact.stat().st_mtime_ns if artifact.is_file() else None
    command = (
        "import config.settings; "
        "import energyplus.baseline.settings; "
        "import energyplus.baseline.normalizer; "
        "import energyplus.baseline.metrics; "
        "import energyplus.baseline.artifacts; "
        "from ui.phase5 import render_phase5; "
        "import app; "
        "print('imports passed')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "imports passed"
    after = artifact.stat().st_mtime_ns if artifact.is_file() else None
    assert after == before


def test_importing_app_does_not_run_or_build_baseline() -> None:
    app_path = Path(__file__).parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")
    compile(source, str(app_path), "exec")
    assert "if st.button(" in source
    assert "Run Official EnergyPlus Baseline" in (
        Path(__file__).parents[1] / "ui" / "phase5.py"
    ).read_text(encoding="utf-8")


def test_optional_pmv_fields_are_import_safe() -> None:
    module = importlib.import_module("energyplus.baseline.normalizer")
    assert "pmv" in module.ZONE_TELEMETRY_COLUMNS
    assert "ppd_percent" in module.ZONE_TELEMETRY_COLUMNS
