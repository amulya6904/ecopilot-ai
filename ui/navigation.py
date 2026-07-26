"""Compact grouped native navigation for the EcoPilot application shell."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NavigationPage:
    group: str
    title: str
    path: str
    icon: str
    default: bool = False


PAGE_DEFINITIONS = (
    NavigationPage(
        "OVERVIEW", "Home", "app_pages/home.py", ":material/home:", True
    ),
    NavigationPage(
        "OVERVIEW",
        "Architecture",
        "app_pages/architecture.py",
        ":material/account_tree:",
    ),
    NavigationPage(
        "OVERVIEW",
        "Demo Flow",
        "app_pages/demo_flow.py",
        ":material/play_circle:",
    ),
    NavigationPage(
        "SYSTEM BUILD",
        "01 · Configuration",
        "app_pages/phase1.py",
        ":material/settings:",
    ),
    NavigationPage(
        "SYSTEM BUILD",
        "02 · Development simulator",
        "app_pages/phase2.py",
        ":material/science:",
    ),
    NavigationPage(
        "SYSTEM BUILD",
        "03 · Development baseline",
        "app_pages/phase3.py",
        ":material/timeline:",
    ),
    NavigationPage(
        "SYSTEM BUILD",
        "04 · EnergyPlus integration",
        "app_pages/phase4.py",
        ":material/energy_savings_leaf:",
    ),
    NavigationPage(
        "SYSTEM BUILD",
        "05 · Official baseline",
        "app_pages/phase5.py",
        ":material/database:",
    ),
    NavigationPage(
        "AUTONOMOUS LOOP",
        "06 · MCP tool layer",
        "app_pages/phase6.py",
        ":material/hub:",
    ),
    NavigationPage(
        "AUTONOMOUS LOOP",
        "07 · Local LLM agent",
        "app_pages/phase7.py",
        ":material/psychology:",
    ),
    NavigationPage(
        "AUTONOMOUS LOOP",
        "08 · Runtime control",
        "app_pages/phase8.py",
        ":material/tune:",
    ),
    NavigationPage(
        "AUTONOMOUS LOOP",
        "09 · Safety supervisor",
        "app_pages/phase9.py",
        ":material/shield:",
    ),
    NavigationPage(
        "RESULTS",
        "10 · Quantitative results",
        "app_pages/phase10.py",
        ":material/analytics:",
    ),
    NavigationPage(
        "RESULTS",
        "Evidence & Downloads",
        "app_pages/evidence.py",
        ":material/folder_open:",
    ),
    NavigationPage(
        "RESULTS",
        "Submission Checklist",
        "app_pages/submission_checklist.py",
        ":material/checklist:",
    ),
)

PRODUCT_PAGE_DEFINITIONS = (
    NavigationPage(
        "ECOPILOT", "Command Center", "app_pages/command_center.py",
        ":material/dashboard:", True
    ),
    NavigationPage(
        "ECOPILOT", "AI Copilot", "app_pages/ai_copilot.py",
        ":material/chat:"
    ),
    NavigationPage(
        "OPERATIONS", "Building", "app_pages/building.py",
        ":material/apartment:"
    ),
    NavigationPage(
        "OPERATIONS", "Analytics", "app_pages/analytics.py",
        ":material/monitoring:"
    ),
    NavigationPage(
        "OPERATIONS", "Decisions", "app_pages/decisions.py",
        ":material/rule:"
    ),
    NavigationPage(
        "ASSURANCE", "Safety", "app_pages/safety.py",
        ":material/shield:"
    ),
    NavigationPage(
        "ASSURANCE", "EnergyPlus", "app_pages/energyplus.py",
        ":material/energy_savings_leaf:"
    ),
    NavigationPage(
        "ASSURANCE", "Reports", "app_pages/reports.py",
        ":material/folder_open:"
    ),
)

DEVELOPER_PAGE_DEFINITIONS = (
    NavigationPage(
        "DEVELOPER", "Technical Evidence",
        "app_pages/technical_evidence.py", ":material/biotech:"
    ),
    NavigationPage(
        "DEVELOPER", "11 · Submission UI",
        "app_pages/phase11.py", ":material/web:"
    ),
    *(
        NavigationPage(
            "DEVELOPER",
            definition.title,
            definition.path,
            definition.icon,
        )
        for definition in PAGE_DEFINITIONS
    ),
)

HIDDEN_PAGE_DEFINITIONS = (
    NavigationPage(
        "DEMO", "Guided Demo", "app_pages/guided_demo.py",
        ":material/play_arrow:"
    ),
)


def build_navigation(streamlit):
    """Build the product IA while keeping every legacy route addressable."""
    groups: dict[str, list[object]] = {}
    for definition in PRODUCT_PAGE_DEFINITIONS:
        visible_title = (
            "Ask EcoPilot"
            if definition.path == "app_pages/ai_copilot.py"
            else definition.title
        )
        groups.setdefault(definition.group, []).append(
            streamlit.Page(
                definition.path,
                title=visible_title,
                icon=definition.icon,
                default=definition.default,
            )
        )

    developer_mode = bool(
        streamlit.session_state.get("developer_mode", False)
    )
    for definition in (*DEVELOPER_PAGE_DEFINITIONS, *HIDDEN_PAGE_DEFINITIONS):
        visible = developer_mode and definition.group == "DEVELOPER"
        group = definition.group if visible else "_HIDDEN"
        groups.setdefault(group, []).append(
            streamlit.Page(
                definition.path,
                title=definition.title,
                icon=definition.icon,
                default=False,
                visibility="visible" if visible else "hidden",
            )
        )
    return streamlit.navigation(groups, position="sidebar", expanded=True)


__all__ = [
    "DEVELOPER_PAGE_DEFINITIONS",
    "HIDDEN_PAGE_DEFINITIONS",
    "PAGE_DEFINITIONS",
    "PRODUCT_PAGE_DEFINITIONS",
    "NavigationPage",
    "build_navigation",
]
