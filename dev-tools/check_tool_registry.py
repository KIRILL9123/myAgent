"""Fail fast when the assistant tool contract drifts across layers."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.agent.tool_registry import (  # noqa: E402
    AVAILABLE_TOOLS,
    TOOL_REGISTRY,
    check_registry_integrity,
)


def main() -> int:
    errors = check_registry_integrity()
    if errors:
        print("Tool registry drift detected:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Tool registry is consistent: {len(TOOL_REGISTRY)} tools, {len(AVAILABLE_TOOLS)} LLM schemas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
