from pathlib import Path

from ui.formatting import (
    format_carbon,
    format_comfort,
    format_cost,
    format_demand,
    format_energy,
    format_percent,
    peak_change_label,
    project_relative,
)


def test_number_formatting_rounds_display_only():
    assert format_energy(58568.21190808615) == "58,568.21 kWh"
    assert format_energy(5.626075812324416, compact=True) == "5.626 kWh"
    assert format_percent(0.009606022839067856, 4) == "0.0096%"
    assert format_demand(21.050576908787157) == "21.051 kW"
    assert format_comfort(23.39254615116684) == "23.39%"
    assert format_cost(45.00860649859533) == "INR 45.01"
    assert format_carbon(3.983261675130052) == "3.98 kg CO₂"


def test_peak_wording_and_relative_path_boundary(tmp_path):
    assert peak_change_label(-3.436766604636432e-07, tolerance_kw=1e-6) == (
        "Essentially unchanged"
    )
    root = tmp_path / "project"
    file_path = root / "results" / "summary.json"
    file_path.parent.mkdir(parents=True)
    file_path.touch()
    assert project_relative(file_path, root) == "results/summary.json"
    assert project_relative(tmp_path / "outside.json", root) == (
        "Outside approved project scope"
    )
