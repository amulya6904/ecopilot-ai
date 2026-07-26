from pathlib import Path


def test_phase12_claims_preserve_scope_and_pmv_disclosure():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("ui/demo").glob("*.py")
    )
    assert "Peak demand essentially unchanged" in source
    assert "PMV unavailable in retained EnergyPlus model" in source
    assert "Derived from configured assumption" in source
    assert "Whole-building effect is small because one zone is controlled" in source
    assert "Comfort fully maintained" not in source
    assert "currently running EnergyPlus" not in source
