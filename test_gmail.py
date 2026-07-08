import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
print("GMAIL_USERNAME:", repr(os.getenv("GMAIL_USERNAME")))
print("GMAIL_APP_PASSWORD:", repr(os.getenv("GMAIL_APP_PASSWORD")))
print("UKRNET_USERNAME:", repr(os.getenv("UKRNET_USERNAME")))
