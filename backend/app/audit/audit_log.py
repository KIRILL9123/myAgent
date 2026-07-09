import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

# Setup logging with rotation
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "audit.log"

logger = logging.getLogger("home_agent_audit")
logger.setLevel(logging.INFO)

# Prevent handler duplication if the module is imported multiple times
if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler = RotatingFileHandler(
        str(LOG_FILE),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def log_action(action_name: str, status: str, details: str = ""):
    """
    Logs an agent action for auditing purposes.
    """
    message = f"Action: {action_name} | Status: {status} | Details: {details}"
    logger.info(message)
    # Also print to console for development visibility
    print(f"[AUDIT] {message}")
