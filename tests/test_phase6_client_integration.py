from pathlib import Path
import asyncio
import pytest
from scripts.test_phase6_mcp_client import smoke_test


@pytest.mark.energyplus
def test_real_stdio_client():
    if not Path("results/official/phase5_energyplus_baseline_summary.json").is_file():
        pytest.skip("Official Phase 5 artifacts are not present.")
    assert asyncio.run(smoke_test()) == 0
