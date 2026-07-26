from mcp_service.tools.baseline_tools import (
    get_baseline_manifest, get_official_baseline_summary, run_official_baseline,
)
from dataclasses import replace
import time


def test_baseline_artifacts_and_run(phase6_context):
    assert get_official_baseline_summary(phase6_context)["data"]["official_result"] is True
    assert get_baseline_manifest(phase6_context)["data"]["executable_path"] == "[configured local path]"
    assert run_official_baseline(phase6_context)["success"] is True


def test_execution_lock(phase6_context):
    phase6_context.execution_lock.acquire()
    try:
        response = run_official_baseline(phase6_context)
        assert response["error"]["code"] == "RUN_ALREADY_IN_PROGRESS"
    finally:
        phase6_context.execution_lock.release()


def test_execution_timeout_releases_lock(phase6_context):
    phase6_context.settings = replace(phase6_context.settings, tool_timeout_seconds=1)
    original = phase6_context.baseline_runner
    def slow_runner(*args, **kwargs):
        time.sleep(1.2)
        return original(*args, **kwargs)
    phase6_context.baseline_runner = slow_runner
    response = run_official_baseline(phase6_context)
    assert response["error"]["code"] == "TOOL_TIMEOUT"
    assert phase6_context.execution_lock.acquire(blocking=False)
    phase6_context.execution_lock.release()
