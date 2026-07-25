from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from mcp_service.errors import MCPToolError
from mcp_service.serialization import enforce_response_size, to_json_safe


def test_json_safe_values():
    value = to_json_safe({
        "path": Path("x"), "time": datetime(2026, 1, 1),
        "integer": np.int64(2), "missing": np.nan,
        "frame": pd.DataFrame([{"x": np.float64(1.5)}]),
    })
    assert value["missing"] is None
    assert value["frame"] == [{"x": 1.5}]


def test_byte_limit():
    with pytest.raises(MCPToolError):
        enforce_response_size({"value": "x" * 100}, 10)
