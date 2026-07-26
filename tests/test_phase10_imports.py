def test_phase10_modules_import_without_running_a_comparison():
    import comparison
    import comparison.artifact_loader
    import comparison.runner
    import ui.phase10

    assert comparison.COMPARISON_SETTINGS.required_backend == "energyplus"
