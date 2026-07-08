import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import imaplib
host = os.getenv("IMAP_HOST", "imap.mail.me.com")
port = int(os.getenv("IMAP_PORT", "993"))
user = os.getenv("IMAP_USERNAME")
pwd = os.getenv("IMAP_PASSWORD")

try:
    conn = imaplib.IMAP4_SSL(host, port)
    print(f"Connected to {host}:{port}")
    conn.login(user, pwd)
    print("Login successful!")
    conn.select("INBOX", readonly=True)
    status, data = conn.search(None, "UNSEEN")
    msg_ids = data[0].split()
    print(f"Unread messages: {len(msg_ids)}")
    conn.close()
    conn.logout()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
