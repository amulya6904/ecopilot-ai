"""Grouped native Streamlit navigation for the Phase 11 application shell."""

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
        "Overview", "Home", "app_pages/home.py", ":material/home:", True
    ),
    NavigationPage(
        "Overview",
        "Architecture",
        "app_pages/architecture.py",
        ":material/account_tree:",
    ),
    NavigationPage(
        "Overview",
        "Demo flow",
        "app_pages/demo_flow.py",
        ":material/play_circle:",
    ),
    NavigationPage(
        "Development foundation",
        "Phase 1 · Configuration",
        "app_pages/phase1.py",
        ":material/settings:",
    ),
    NavigationPage(
        "Development foundation",
        "Phase 2 · Lightweight simulator",
        "app_pages/phase2.py",
        ":material/science:",
    ),
    NavigationPage(
        "Development foundation",
        "Phase 3 · Development baseline",
        "app_pages/phase3.py",
        ":material/timeline:",
    ),
    NavigationPage(
        "Official EnergyPlus pipeline",
        "Phase 4 · EnergyPlus integration",
        "app_pages/phase4.py",
        ":material/energy_savings_leaf:",
    ),
    NavigationPage(
        "Official EnergyPlus pipeline",
        "Phase 5 · Official baseline",
        "app_pages/phase5.py",
        ":material/database:",
    ),
    NavigationPage(
        "Official EnergyPlus pipeline",
        "Phase 6 · MCP tool layer",
        "app_pages/phase6.py",
        ":material/hub:",
    ),
    NavigationPage(
        "Official EnergyPlus pipeline",
        "Phase 7 · Open-source LLM",
        "app_pages/phase7.py",
        ":material/psychology:",
    ),
    NavigationPage(
        "Official EnergyPlus pipeline",
        "Phase 8 · Runtime control",
        "app_pages/phase8.py",
        ":material/tune:",
    ),
    NavigationPage(
        "Official EnergyPlus pipeline",
        "Phase 9 · Safety supervisor",
        "app_pages/phase9.py",
        ":material/shield:",
    ),
    NavigationPage(
        "Official EnergyPlus pipeline",
        "Phase 10 · Quantitative results",
        "app_pages/phase10.py",
        ":material/analytics:",
    ),
    NavigationPage(
        "Submission",
        "Evidence & downloads",
        "app_pages/evidence.py",
        ":material/folder_open:",
    ),
    NavigationPage(
        "Submission",
        "Submission checklist",
        "app_pages/submission_checklist.py",
        ":material/checklist:",
    ),
)


def build_navigation(streamlit):
    groups: dict[str, list[object]] = {}
    for definition in PAGE_DEFINITIONS:
        groups.setdefault(definition.group, []).append(
            streamlit.Page(
                definition.path,
                title=definition.title,
                icon=definition.icon,
                default=definition.default,
            )
        )
    return streamlit.navigation(groups, position="sidebar", expanded=True)


__all__ = ["PAGE_DEFINITIONS", "NavigationPage", "build_navigation"]
