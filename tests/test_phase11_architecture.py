from ui.architecture import ARCHITECTURE_FLOW, SAFETY_REASONS, TECHNOLOGY_ROWS


def test_architecture_flow_and_trust_layers_are_complete():
    assert ARCHITECTURE_FLOW[0] == "EnergyPlus Runtime"
    assert ARCHITECTURE_FLOW[-1] == "Fallback / Rollback"
    assert len(ARCHITECTURE_FLOW) == 10
    assert len(SAFETY_REASONS) == 8
    technologies = {row[0] for row in TECHNOLOGY_ROWS}
    assert {
        "Python 3.12",
        "EnergyPlus 26.1",
        "Ollama",
        "qwen3:4b",
        "MCP",
        "Streamlit + Altair",
    } <= technologies
