from ui.demo_flow import DEMO_STEPS


def test_demo_flow_has_nine_verified_artifact_backed_steps():
    assert len(DEMO_STEPS) == 9
    assert all(step.status == "Verified" for step in DEMO_STEPS)
    assert all(step.artifact.startswith("results/") for step in DEMO_STEPS)
    assert all(step.page.startswith("app_pages/") for step in DEMO_STEPS)
    assert "baseline" in DEMO_STEPS[0].title.lower()
    assert "comparison" in DEMO_STEPS[-1].title.lower()
