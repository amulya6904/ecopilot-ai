"""Import and syntax smoke tests without starting Streamlit."""

import importlib
from pathlib import Path


def test_configuration_modules_import() -> None:
    importlib.import_module("config.settings")
    importlib.import_module("config.zones")


def test_app_compiles_without_starting_streamlit() -> None:
    app_path = Path(__file__).parents[1] / "app.py"
    compile(app_path.read_text(encoding="utf-8"), str(app_path), "exec")
