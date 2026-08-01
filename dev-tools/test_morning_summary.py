#!/usr/bin/env python3
\"\"\"
Dev-tool: trigger the morning summary task directly.
WARNING: This script connects to real CalDAV/IMAP services and can send
real Telegram messages. It REQUIRES EXECUTION_MODE=real to run.
\"\"\"
import os
import sys
import asyncio

# Safety: require explicit REAL mode for this script
if os.getenv("EXECUTION_MODE", "dry_run").strip().lower() != "real":
    print("ERROR: This script requires EXECUTION_MODE=real. Aborting for safety.")
    print("Set EXECUTION_MODE=real in your .env file or environment, then re-run.")
    sys.exit(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.agent.scheduled_tasks import morning_summary

if __name__ == "__main__":
    asyncio.run(morning_summary())
