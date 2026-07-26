import inspect

import energyplus.runtime_control.callbacks as callbacks
import safety
import safety.settings
import safety.supervisor


def test_safety_modules_do_not_execute_shell_or_write_actuator():
    source = "\n".join(
        inspect.getsource(module)
        for module in (
            safety.settings,
            safety.supervisor,
        )
    ).casefold()
    assert "subprocess" not in source
    assert "os.system" not in source
    assert "set_actuator_value" not in source


def test_single_actuator_write_remains_behind_phase9_decision():
    source = inspect.getsource(callbacks.RuntimeCallbacks.on_control)
    assert source.count("set_actuator_value") == 1
    assert "active_safety_decision" in source
    assert "evaluate_action_safety" not in source
    assert safety.SAFETY_SETTINGS.autonomous_bypass_allowed is False
