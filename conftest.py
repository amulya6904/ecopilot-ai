"""Cross-platform pytest startup configuration."""

import os
from pathlib import Path
import tempfile
import uuid


def pytest_configure(config) -> None:
    """Use a private per-run temp directory instead of pytest's shared user root."""
    if config.option.basetemp is None:
        run_id = f"ecopilot-pytest-{os.getpid()}-{uuid.uuid4().hex}"
        config.option.basetemp = Path(tempfile.gettempdir()) / run_id
