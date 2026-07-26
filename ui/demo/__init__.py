"""Phase 12 product-experience presentation package.

This package reads persisted Phase 7–10 evidence and delegates any optional
live work to the already validated service boundaries. It contains no
EnergyPlus, actuator, safety, MCP, or comparison business logic.
"""

from .data import (
    ArtifactLoadError,
    DemoArtifactIndex,
    latest_artifact_index,
    load_demo_context,
)

__all__ = [
    "ArtifactLoadError",
    "DemoArtifactIndex",
    "latest_artifact_index",
    "load_demo_context",
]
