"""Compatibility facade for the centralized tool permission registry."""

from backend.app.agent.tool_registry import PermissionLevel, TOOL_REGISTRY


def load_permissions() -> dict[str, PermissionLevel]:
    """Return a snapshot for callers that still need the old helper."""
    return {name: spec.permission for name, spec in TOOL_REGISTRY.items()}


def check_permission(action_name: str) -> PermissionLevel | None:
    """Return the permission declared by the central tool registry."""
    spec = TOOL_REGISTRY.get(action_name)
    return spec.permission if spec else None
