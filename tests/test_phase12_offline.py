from pathlib import Path


def test_phase12_ui_has_no_remote_assets_or_standalone_limitations_page():
    paths = (
        Path("app.py"),
        Path("assets/ecopilot.css"),
        *Path("ui/demo").glob("*.py"),
        *Path("app_pages").glob("*.py"),
    )
    for path in paths:
        source = path.read_text(encoding="utf-8").lower()
        assert "https://" not in source, path
        assert "fonts.googleapis.com" not in source, path
        assert "<script" not in source, path
    assert not Path("app_pages/limitations.py").exists()

