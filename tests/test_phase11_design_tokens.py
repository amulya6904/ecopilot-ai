from ui.theme import STYLESHEET, build_stylesheet
from ui.tokens import TOKENS


def test_editorial_design_tokens_match_the_frozen_palette():
    assert TOKENS.canvas == "#F5F2EB"
    assert TOKENS.canvas_soft == "#FAF8F3"
    assert TOKENS.surface == "#FFFFFF"
    assert TOKENS.ink == "#171714"
    assert TOKENS.action == "#11110F"
    assert TOKENS.verified == "#2F654D"
    assert TOKENS.warning == "#8A641D"
    assert TOKENS.error == "#8D3C35"
    assert TOKENS.chart_baseline == "#2A2925"
    assert TOKENS.chart_controlled == "#718777"


def test_single_local_stylesheet_builds_without_remote_dependencies():
    assert STYLESHEET.is_file()
    css = build_stylesheet()
    assert css.count("<style>") == 1
    assert "--ep-canvas: #F5F2EB" in css
    assert "Helvetica Neue" in css
    assert "https://" not in css
    assert "<script" not in css.lower()
