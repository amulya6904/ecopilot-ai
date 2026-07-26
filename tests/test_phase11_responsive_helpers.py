from pathlib import Path


def test_stylesheet_has_desktop_tablet_mobile_and_accessibility_rules():
    css = Path("assets/ecopilot.css").read_text(encoding="utf-8")
    assert "--ep-content-width" in css or "var(--ep-content-width)" in css
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 640px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ":focus-visible" in css
    assert "min(86vw, var(--ep-sidebar-width))" in css
