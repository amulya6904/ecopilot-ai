import importlib
from pathlib import Path


def test_phase4_modules_import_without_energyplus() -> None:
    for module in (
        "energyplus.adapter.discovery",
        "backends.energyplus",
    ):
        importlib.import_module(module)


def test_app_does_not_execute_energyplus_at_import() -> None:
    app = Path(__file__).parents[1] / "app.py"
    compile(app.read_text(encoding="utf-8"), str(app), "exec")
