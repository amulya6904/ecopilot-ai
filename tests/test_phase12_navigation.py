from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.navigation import (
    DEVELOPER_PAGE_DEFINITIONS,
    PAGE_DEFINITIONS,
    PRODUCT_PAGE_DEFINITIONS,
)


def test_product_navigation_is_default_and_complete():
    assert [page.title for page in PRODUCT_PAGE_DEFINITIONS] == [
        "Command Center",
        "AI Copilot",
        "Building",
        "Analytics",
        "Decisions",
        "Safety",
        "EnergyPlus",
        "Reports",
    ]
    assert PRODUCT_PAGE_DEFINITIONS[0].default is True
    assert sum(page.default for page in PRODUCT_PAGE_DEFINITIONS) == 1
    assert all(Path(page.path).is_file() for page in PRODUCT_PAGE_DEFINITIONS)

    app = AppTest.from_file("app.py", default_timeout=120).run()
    assert not app.exception
    assert [title.value for title in app.title] == ["EcoPilot AI"]


def test_legacy_routes_remain_registered_for_developer_mode():
    assert len(PAGE_DEFINITIONS) == 15
    assert any(page.title == "11 · Submission UI" for page in DEVELOPER_PAGE_DEFINITIONS)
    assert all(Path(page.path).is_file() for page in DEVELOPER_PAGE_DEFINITIONS)

