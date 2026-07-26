from pathlib import Path

from streamlit.testing.v1 import AppTest
from ui.constants import PROJECT_SUBTITLE, PROJECT_TITLE
from ui.home import CORE_BLOCKS, HERO_PARAGRAPH, SYSTEM_STATUS


def test_home_constants_and_eight_system_blocks():
    assert PROJECT_TITLE == "EcoPilot AI"
    assert PROJECT_SUBTITLE == (
        "Safety-Supervised Autonomous EnergyPlus Building Control"
    )
    assert HERO_PARAGRAPH.startswith("EcoPilot AI connects")
    assert len(CORE_BLOCKS) == 8
    assert len(SYSTEM_STATUS) == 6


def test_home_renders_verified_status_and_measured_result():
    page = AppTest.from_file("app.py", default_timeout=30).run()
    assert not page.exception
    assert [item.value for item in page.title] == ["EcoPilot AI"]
    labels = {item.label for item in page.metric}
    assert {
        "Verified facility-energy reduction",
        "Reproducible annual reduction",
        "Comfort-proxy change",
        "Peak demand",
    } <= labels
    source = Path("ui/home.py").read_text(encoding="utf-8")
    assert "View Quantitative Results" in source
    assert "Conservative single-zone" in source
