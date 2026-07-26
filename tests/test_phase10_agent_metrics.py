from comparison.agent_metrics import calculate_agent_metrics


def test_agent_evidence_and_structured_output_metrics():
    result = calculate_agent_metrics(
        [{"source": "phase10_reproducible_policy", "confidence": 0.7}],
        control_mode="reproducible_policy",
        valid_structured_outputs=1,
        invalid_structured_outputs=1,
        self_corrections=1,
    )
    assert result.decisions_using_official_energyplus_evidence == 1
    assert result.structured_output_success_rate == 50.0
    assert result.self_corrections == 1
