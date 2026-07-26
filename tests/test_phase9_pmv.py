from safety.fault_injection import make_candidate, make_state
from safety.pmv import evaluate_pmv_rules


def test_genuine_pmv_hot_cold_and_ppd_rules():
    hot = evaluate_pmv_rules(
        make_state(pmv=0.8, ppd_percent=25.0), make_candidate()
    )
    assert any(item.rule_id == "PMV_HOT_LIMIT" and not item.passed for item in hot)
    assert any(item.rule_id == "PPD_WARNING_ACTIVE" and not item.passed for item in hot)
    cold = evaluate_pmv_rules(
        make_state(pmv=-0.8), make_candidate(requested=21.0)
    )
    assert any(item.rule_id == "PMV_COLD_LIMIT" and not item.passed for item in cold)


def test_missing_pmv_is_explicit_warning_not_fabricated_value():
    rules = evaluate_pmv_rules(make_state(pmv=None), make_candidate())
    assert [item.rule_id for item in rules] == [
        "PMV_UNAVAILABLE_USING_TEMPERATURE_PROXY"
    ]
    assert rules[0].severity == "warning"
