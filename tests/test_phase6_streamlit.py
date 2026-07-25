"""Headless navigation verification for all six Streamlit pages."""

from streamlit.testing.v1 import AppTest


def test_all_six_streamlit_pages_render_without_exceptions():
    app = AppTest.from_file("app.py", default_timeout=30)
    app.run()
    assert not app.exception
    navigation = app.sidebar.radio[0]
    assert len(navigation.options) == 6
    for page in navigation.options:
        navigation.set_value(page)
        app.run()
        assert not app.exception, f"Streamlit page failed: {page}"
