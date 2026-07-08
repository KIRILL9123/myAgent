import json
from pathlib import Path
from enum import Enum

class PermissionLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

def load_permissions() -> dict[str, PermissionLevel]:
    config_path = Path(__file__).parent / "tool_permissions.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {item["action_name"]: PermissionLevel(item["permission_level"]) for item in data}
    except Exception as e:
        # Default to strict mode if config is missing or corrupted
        print(f"[WARNING] Failed to load permissions: {e}")
        return {}

# Load once at module import
_PERMISSIONS = load_permissions()

def check_permission(action_name: str) -> PermissionLevel | None:
    """
    Checks the permission level of a given action.
    Returns the PermissionLevel, or None if the action is unknown.
    """
    return _PERMISSIONS.get(action_name)
