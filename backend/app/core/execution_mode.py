import logging
import os
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    DRY_RUN = "dry_run"
    REAL = "real"


def get_execution_mode() -> ExecutionMode:
    raw = os.getenv("EXECUTION_MODE", "dry_run").strip().lower()
    try:
        return ExecutionMode(raw)
    except ValueError:
        logger.warning(
            "Invalid EXECUTION_MODE=%r — falling back to DRY_RUN (safe default). "
            "Valid values: 'dry_run', 'real'.",
            raw,
        )
        return ExecutionMode.DRY_RUN


def is_dry_run() -> bool:
    return get_execution_mode() == ExecutionMode.DRY_RUN
