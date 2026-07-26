from pathlib import Path


RUNTIME_SOURCES = (
    Path("app.py"),
    *sorted(Path("app_pages").glob("*.py")),
    *sorted(Path("ui").glob("*.py")),
    Path(".streamlit/config.toml"),
)


def test_streamlit_runtime_uses_no_external_assets_or_unsafe_markup():
    forbidden = (
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "unpkg.com",
        "unsafe_allow_html=true",
        "<script",
        "st.components.v1.html",
    )
    for path in RUNTIME_SOURCES:
        text = path.read_text(encoding="utf-8").lower()
        assert "https://" not in text, path
        assert not any(token in text for token in forbidden), path
