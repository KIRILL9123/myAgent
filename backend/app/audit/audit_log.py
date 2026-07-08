import logging
from datetime import datetime
from pathlib import Path

# Setup basic logging to a file
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "audit.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_action(action_name: str, status: str, details: str = ""):
    """
    Logs an agent action for auditing purposes.
    """
    message = f"Action: {action_name} | Status: {status} | Details: {details}"
    logging.info(message)
    # Also print to console for development visibility
    print(f"[AUDIT] {message}")
