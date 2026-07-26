from ui.demo_flow import DEMO_STEPS


def test_demo_flow_has_ten_verified_artifact_backed_steps():
    assert len(DEMO_STEPS) == 10
    assert all(step.status == "Verified" for step in DEMO_STEPS)
    assert all(step.artifact.startswith("results/") for step in DEMO_STEPS)
    assert all(step.page.startswith("app_pages/") for step in DEMO_STEPS)
    assert "baseline" in DEMO_STEPS[0].title.lower()
    assert "comparison" in DEMO_STEPS[-1].title.lower()
    assert [step.number for step in DEMO_STEPS] == [
        f"{number:02d}" for number in range(1, 11)
    ]
