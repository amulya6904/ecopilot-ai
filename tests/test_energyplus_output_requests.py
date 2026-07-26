from hashlib import sha256
from pathlib import Path

from config.settings import ENERGYPLUS
from energyplus.adapter.output_requests import (
    ensure_phase4_output_requests,
    inspect_output_requests,
)


def test_derived_model_has_requests_and_preserves_base() -> None:
    source = Path(ENERGYPLUS.source_model_path)
    before = sha256(source.read_bytes()).hexdigest()
    destination = ensure_phase4_output_requests(source, ENERGYPLUS.base_model_path)
    after = sha256(source.read_bytes()).hexdigest()
    assert before == after
    assert destination != source.resolve()
    assert all(inspect_output_requests(destination).values())
    assert "EcoPilot AI Phase 4 telemetry additions" in destination.read_text(
        encoding="utf-8"
    )
