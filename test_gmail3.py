import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from backend.app.connectors.mail_connector import list_unread_emails
print(list_unread_emails(account="gmail", limit=2))
