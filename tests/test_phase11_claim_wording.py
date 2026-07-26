from pathlib import Path

from ui.constants import COMFORT_WORDING, HONEST_RESULT_CLAIM, SMALL_RESULT_NOTE


def test_exact_honest_claim_and_context_wording_are_frozen():
    assert HONEST_RESULT_CLAIM == (
        "Under a fully aligned and reproducible EnergyPlus experiment, the "
        "safety-supervised one-zone control policy reduced annual facility "
        "electricity by approximately 5.626 kWh, or 0.0096%. "
        "Occupied-temperature proxy compliance improved slightly relative to "
        "the fixed-schedule baseline, while peak demand remained effectively "
        "unchanged."
    )
    assert COMFORT_WORDING == (
        "Configured occupied-temperature proxy did not degrade relative to "
        "baseline."
    )
    assert "small" in SMALL_RESULT_NOTE
    assert "one zone" in SMALL_RESULT_NOTE


def test_contextual_disclosures_exist_without_a_limitations_page():
    text_by_path = {
        path: path.read_text(encoding="utf-8").lower()
        for path in (
            Path("ui/home.py"),
            Path("ui/architecture.py"),
            Path("ui/phase7.py"),
            Path("ui/phase9.py"),
            Path("ui/phase10.py"),
            Path("README.md"),
            Path("docs/SYSTEM_ARCHITECTURE.md"),
            Path("docs/FINAL_RESULTS.md"),
            Path("docs/SUBMISSION_CHECKLIST.md"),
        )
    }
    assert "conservative single-zone" in text_by_path[Path("ui/home.py")]
    assert "deterministic authority" in text_by_path[Path("ui/architecture.py")]
    assert "hardware-dependent" in text_by_path[Path("ui/phase7.py")]
    assert "prototype project guardrails" in text_by_path[Path("ui/phase9.py")]
    assert "essentially unchanged" in text_by_path[Path("ui/phase10.py")]
    assert not Path("app_pages/limitations.py").exists()
    assert not Path("docs/LIMITATIONS.md").exists()
