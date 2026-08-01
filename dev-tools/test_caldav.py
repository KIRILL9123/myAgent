#!/usr/bin/env python3
\"\"\"
Dev-tool: list CalDAV events for a specific date.
Read-only operation — safe to run in any mode, but requires valid CalDAV
credentials to actually connect.
\"\"\"
from backend.app.connectors.caldav_connector import list_events
import json
print(json.dumps(list_events("2026-07-02T00:00:00", "2026-07-02T23:59:59"), indent=2))
