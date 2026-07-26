from pathlib import Path

from streamlit.testing.v1 import AppTest
from ui.constants import PROJECT_STATEMENT, PROJECT_SUBTITLE, PROJECT_TITLE
from ui.home import CORE_BLOCKS


def test_home_constants_and_six_system_blocks():
    assert PROJECT_TITLE == "EcoPilot AI"
    assert PROJECT_SUBTITLE == (
        "Safety-Supervised Autonomous EnergyPlus Building Control"
    )
    assert PROJECT_STATEMENT.startswith("EcoPilot AI combines EnergyPlus")
    assert len(CORE_BLOCKS) == 6


def test_home_renders_verified_status_and_measured_result():
    page = AppTest.from_file("app.py", default_timeout=30).run()
    assert not page.exception
    assert [item.value for item in page.title] == ["EcoPilot AI"]
    labels = {item.label for item in page.metric}
    assert {
        "EnergyPlus integration",
        "MCP tools",
        "Local LLM",
        "Control injection",
        "Safety validation",
        "Official comparison",
        "Severe errors",
        "Fatal errors",
        "Facility-energy reduction",
        "Percentage reduction",
        "Comfort proxy change",
        "Peak demand",
    } <= labels
    assert "Scope and assumptions" in Path("ui/home.py").read_text(
        encoding="utf-8"
    )
