from ui.evidence import GROUP_ORDER
from ui.submission import build_checklist


def test_evidence_groups_and_submission_sections_match_demo_contract():
    assert GROUP_ORDER == (
        "Official baseline",
        "MCP verification",
        "LLM evidence",
        "Runtime actuator proof",
        "Safety validation",
        "Quantitative comparison",
        "Reproducibility",
        "Submission package",
    )
    assert tuple(build_checklist()) == (
        "Repository",
        "Models",
        "Evidence",
        "Deliverables",
    )
