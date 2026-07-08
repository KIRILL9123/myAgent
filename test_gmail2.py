import os, sys
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
