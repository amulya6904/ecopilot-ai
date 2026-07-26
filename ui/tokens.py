"""Semantic visual tokens for EcoPilot's offline editorial interface."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignTokens:
    """One source of truth for presentation colors and geometry."""

    canvas: str = "#F5F2EB"
    canvas_soft: str = "#FAF8F3"
    surface: str = "#FFFFFF"
    ink: str = "#171714"
    ink_secondary: str = "#55534D"
    ink_muted: str = "#86827A"
    border: str = "#DDD8CE"
    border_strong: str = "#BBB5AA"
    action: str = "#11110F"
    action_hover: str = "#2A2925"
    on_action: str = "#FFFFFF"
    verified: str = "#2F654D"
    verified_bg: str = "#E8F0EA"
    warning: str = "#8A641D"
    warning_bg: str = "#F4ECD9"
    error: str = "#8D3C35"
    error_bg: str = "#F2E4E2"
    info: str = "#506574"
    info_bg: str = "#E7EDF0"
    navy: str = "#17324D"
    navy_soft: str = "#E8EEF3"
    amber: str = "#C47A24"
    amber_soft: str = "#F6EAD9"
    telemetry: str = "#4F7594"
    chart_baseline: str = "#2A2925"
    chart_controlled: str = "#718777"
    chart_requested: str = "#A69C8C"
    chart_approved: str = "#2F654D"
    chart_fallback: str = "#A77821"
    chart_emergency: str = "#8D3C35"
    radius_small: str = "2px"
    radius_medium: str = "4px"
    radius_large: str = "14px"
    content_width: str = "1260px"
    sidebar_width: str = "286px"

    def css_variables(self) -> str:
        """Return CSS variables without introducing a second token registry."""
        pairs = {
            "--ep-canvas": self.canvas,
            "--ep-canvas-soft": self.canvas_soft,
            "--ep-surface": self.surface,
            "--ep-ink": self.ink,
            "--ep-ink-secondary": self.ink_secondary,
            "--ep-ink-muted": self.ink_muted,
            "--ep-border": self.border,
            "--ep-border-strong": self.border_strong,
            "--ep-action": self.action,
            "--ep-action-hover": self.action_hover,
            "--ep-on-action": self.on_action,
            "--ep-verified": self.verified,
            "--ep-verified-bg": self.verified_bg,
            "--ep-warning": self.warning,
            "--ep-warning-bg": self.warning_bg,
            "--ep-error": self.error,
            "--ep-error-bg": self.error_bg,
            "--ep-info": self.info,
            "--ep-info-bg": self.info_bg,
            "--ep-navy": self.navy,
            "--ep-navy-soft": self.navy_soft,
            "--ep-amber": self.amber,
            "--ep-amber-soft": self.amber_soft,
            "--ep-telemetry": self.telemetry,
            "--ep-chart-baseline": self.chart_baseline,
            "--ep-chart-controlled": self.chart_controlled,
            "--ep-chart-requested": self.chart_requested,
            "--ep-chart-approved": self.chart_approved,
            "--ep-chart-fallback": self.chart_fallback,
            "--ep-chart-emergency": self.chart_emergency,
            "--ep-radius-sm": self.radius_small,
            "--ep-radius-md": self.radius_medium,
            "--ep-radius-lg": self.radius_large,
            "--ep-content-width": self.content_width,
            "--ep-sidebar-width": self.sidebar_width,
        }
        return "\n".join(f"{name}: {value};" for name, value in pairs.items())


TOKENS = DesignTokens()

CHART_COLORS = {
    "Fixed-schedule baseline": TOKENS.chart_baseline,
    "Safety-supervised controlled": TOKENS.chart_controlled,
    "Requested": TOKENS.chart_requested,
    "Approved": TOKENS.chart_approved,
    "Applied": TOKENS.chart_approved,
    "Observed": TOKENS.chart_controlled,
    "Configured lower bound": TOKENS.chart_requested,
    "Configured upper bound": TOKENS.chart_requested,
    "Fallback": TOKENS.chart_fallback,
    "Emergency": TOKENS.chart_emergency,
}


__all__ = ["CHART_COLORS", "DesignTokens", "TOKENS"]
