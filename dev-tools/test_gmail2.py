#!/usr/bin/env python3
"""
Dev-tool: test IMAP connection to Gmail.
WARNING: This connects to a real Gmail account if credentials are configured.
It requires EXECUTION_MODE=real to run.
"""
import os
import sys

# Safety: require explicit REAL mode
if os.getenv("EXECUTION_MODE", "dry_run").strip().lower() != "real":
    print("ERROR: This script requires EXECUTION_MODE=real. Aborting for safety.")
    print("Set EXECUTION_MODE=real in your .env file or environment, then re-run.")
    sys.exit(1)

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from backend.app.connectors.mail_connector import _connect
conn = _connect("gmail")
if conn:
    print("SUCCESS")
    conn.logout()
else:
    print("FAILED")
