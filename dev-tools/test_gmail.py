import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

"""Local-only configuration check; never print credential values."""

fields = {
    "GMAIL_USERNAME": bool(os.getenv("GMAIL_USERNAME")),
    "GMAIL_APP_PASSWORD": bool(os.getenv("GMAIL_APP_PASSWORD")),
    "UKRNET_USERNAME": bool(os.getenv("UKRNET_USERNAME")),
    "UKRNET_PASSWORD": bool(os.getenv("UKRNET_PASSWORD")),
}
configured = ", ".join(name for name, present in fields.items() if present) or "none"
print(f"Configured credential fields: {configured}")
