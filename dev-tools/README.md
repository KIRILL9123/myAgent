# Manual integration scripts

Scripts in this directory are operator tools, not part of the automated test
suite. Some of them contact external services or read real local integrations.

- Run the normal checks with `pytest` or `dev-tools/release_gate.py`; pytest is
  restricted to `backend/tests`.
- Run a script here only when you intentionally want to inspect a configured
  integration.
- Never add credential values to output. Configuration checks may report only
  whether a field is present.
- Keep `.env` private. Start from `.env.example`, generate a private API key,
  and explicitly opt into `real` execution or external providers only when
  needed.
- If Windows Firewall blocks a phone on the same LAN, run
  `powershell -ExecutionPolicy Bypass -File .\dev-tools\allow_lan_access.ps1`.
  The script requests UAC and allows only the supplied local subnet (default
  `192.168.2.0/24`) on ports 5173 and 8000.
