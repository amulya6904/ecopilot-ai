import importlib
import subprocess

import httpx

from backends.energyplus import EnergyPlusBackend


def test_phase11_imports_do_not_execute_ollama_energyplus_or_subprocess(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Import attempted an external or expensive operation")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    monkeypatch.setattr(EnergyPlusBackend, "run_simulation", forbidden)
    for name in (
        "ui.constants",
        "ui.tokens",
        "ui.theme",
        "ui.shell",
        "ui.formatting",
        "ui.navigation",
        "ui.charts",
        "ui.home",
        "ui.architecture",
        "ui.demo_flow",
        "ui.evidence",
        "ui.submission",
        "app",
    ):
        importlib.reload(importlib.import_module(name))
