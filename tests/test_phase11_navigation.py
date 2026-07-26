from pathlib import Path

from streamlit.testing.v1 import AppTest

import app
from ui.navigation import PAGE_DEFINITIONS


def test_grouped_navigation_has_all_required_pages_and_no_limitations_page():
    groups = [page.group for page in PAGE_DEFINITIONS]
    assert list(dict.fromkeys(groups)) == [
        "OVERVIEW",
        "SYSTEM BUILD",
        "AUTONOMOUS LOOP",
        "RESULTS",
    ]
    assert len(PAGE_DEFINITIONS) == 15
    assert sum(page.default for page in PAGE_DEFINITIONS) == 1
    assert all(Path(page.path).is_file() for page in PAGE_DEFINITIONS)
    assert "limitations" not in " ".join(
        f"{page.title} {page.path}" for page in PAGE_DEFINITIONS
    ).lower()
    assert all(
        callable(renderer)
        for renderer in (
            app.render_phase1,
            app.render_phase2,
            app.render_phase3,
            app.render_phase4,
        )
    )


def test_judge_mode_condenses_technical_pages_without_hiding_evidence():
    test_app = AppTest.from_file("app.py", default_timeout=30).run()
    assert not test_app.exception
    assert test_app.sidebar.toggle[0].value is True
    test_app.switch_page("app_pages/phase1.py").run()
    assert not test_app.exception
    assert any(
        "Judge Mode · verified artifacts only" in item.value
        for item in test_app.markdown
    )
    assert not test_app.button
