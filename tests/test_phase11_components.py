from ui import components


def test_required_reusable_presentation_components_exist():
    required = (
        "page_header",
        "eyebrow",
        "status_badge",
        "result_metric",
        "compact_metric",
        "evidence_row",
        "section_divider",
        "editorial_callout",
        "primary_button",
        "secondary_button",
        "trust_boundary",
        "methodology_item",
        "artifact_download",
        "empty_state",
        "error_state",
        "scope_note",
    )
    assert all(callable(getattr(components, name)) for name in required)
