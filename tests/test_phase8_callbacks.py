import inspect

from energyplus.runtime_control.callbacks import RuntimeCallbacks


def test_callbacks_register_control_and_observation_points():
    class Runtime:
        def __init__(self): self.names = []
        def callback_after_predictor_before_hvac_managers(self, state, callback):
            self.names.append("control")
        def callback_end_zone_timestep_after_zone_reporting(self, state, callback):
            self.names.append("observation")
    runtime = Runtime()
    handler = object.__new__(RuntimeCallbacks)
    handler.api = type("API", (), {"runtime": runtime})()
    handler.register(object())
    assert runtime.names == ["control", "observation"]


def test_callback_module_has_no_ollama_dependency():
    assert "ollama" not in inspect.getsource(
        __import__(
            "energyplus.runtime_control.callbacks",
            fromlist=["RuntimeCallbacks"],
        )
    ).casefold()
