from streamlit.testing.v1 import AppTest

from ui.demo.data import DEMO_MODE_REPLAY
from ui.demo.guided_demo import SCENES


def test_replay_is_default_and_guided_demo_has_seven_scenes():
    assert len(SCENES) == 7
    app = AppTest.from_file("app.py", default_timeout=120).run()
    assert not app.exception
    assert app.sidebar.selectbox[0].label == "Data source"
    assert app.sidebar.selectbox[0].value == DEMO_MODE_REPLAY
    app.switch_page("app_pages/guided_demo.py").run(timeout=120)
    assert not app.exception
    assert [button.label for button in app.button] == ["Back", "Exit demo", "Next"]

