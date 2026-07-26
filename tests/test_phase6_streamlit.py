"""Headless navigation verification for the complete Streamlit application."""

from streamlit.testing.v1 import AppTest

from ui.navigation import PAGE_DEFINITIONS


def test_all_streamlit_pages_render_without_exceptions():
    app = AppTest.from_file("app.py", default_timeout=60)
    app.run()
    assert not app.exception
    assert len(PAGE_DEFINITIONS) == 15
    app.sidebar.toggle[0].set_value(True).run()
    for page in PAGE_DEFINITIONS:
        app.switch_page(page.path).run(timeout=60)
        assert not app.exception, f"Streamlit page failed: {page.path}"
