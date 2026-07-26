from ui.architecture import ARCHITECTURE_FLOW, LAYER_ROWS, TECHNOLOGY_ROWS


def test_architecture_flow_and_trust_layers_are_complete():
    assert ARCHITECTURE_FLOW[0] == "EnergyPlus"
    assert ARCHITECTURE_FLOW[-1] == "Quantitative comparison"
    assert len(ARCHITECTURE_FLOW) == 11
    assert len(LAYER_ROWS) == 6
    assert {row[0] for row in LAYER_ROWS} == {
        "Simulation engine",
        "Cognitive layer",
        "Communication layer",
        "Safety layer",
        "Runtime-control layer",
        "Evidence and comparison layer",
    }
    technologies = {row[0] for row in TECHNOLOGY_ROWS}
    assert {"Python", "EnergyPlus", "Ollama", "qwen3:4b", "MCP", "Streamlit"} <= technologies
