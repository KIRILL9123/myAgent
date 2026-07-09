import os
import imaplib
import email
import smtplib
from email.header import decode_header
from email.message import Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from typing import Any

load_dotenv()

# Configuration mapping
def _get_account_config(account: str) -> dict[str, str | int] | None:
    if account.lower() == "gmail":
        return {
            "host": os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com"),
            "port": int(os.getenv("GMAIL_IMAP_PORT", "993")),
            "smtp_host": os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("GMAIL_SMTP_PORT", "587")),
            "user": os.getenv("GMAIL_USERNAME"),
            "pwd": os.getenv("GMAIL_APP_PASSWORD"),
        }
    elif account.lower() == "ukrnet":
        return {
            "host": os.getenv("UKRNET_IMAP_HOST", "imap.ukr.net"),
            "port": int(os.getenv("UKRNET_IMAP_PORT", "993")),
            "smtp_host": os.getenv("UKRNET_SMTP_HOST", "smtp.ukr.net"),
            "smtp_port": int(os.getenv("UKRNET_SMTP_PORT", "465")),
            "user": os.getenv("UKRNET_USERNAME"),
            "pwd": os.getenv("UKRNET_PASSWORD"),
        }
    return None


def _decode_header_value(value: str | None) -> str:
    """Decode an email header that may be encoded (RFC 2047)."""
    if not value:
        return ""
    decoded_parts: list[str] = []
    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return " ".join(decoded_parts)


def _get_body_preview(msg: Message, max_chars: int = 300) -> str:
    """Extract a short plain-text preview from the email body."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    return text[:max_chars].strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            return text[:max_chars].strip()
    return ""


def _connect(account: str) -> imaplib.IMAP4_SSL | None:
    """Establish an IMAP connection to the specified account."""
    config = _get_account_config(account)
    if not config or not config["user"] or not config["pwd"]:
        print(f"[MAIL] Credentials not configured for account: {account}")
        return None
    try:
        conn = imaplib.IMAP4_SSL(config["host"], config["port"])
        conn.login(config["user"], config["pwd"])
        return conn
    except Exception as e:
        print(f"[MAIL] Failed to connect to {account}: {e}")
        return None


def _parse_email(raw_data: bytes) -> dict[str, Any]:
    """Parse a raw email into a structured dict."""
    msg = email.message_from_bytes(raw_data)
    return {
        "from": _decode_header_value(msg.get("From")),
        "to": _decode_header_value(msg.get("To")),
        "subject": _decode_header_value(msg.get("Subject")),
        "date": msg.get("Date", ""),
        "preview": _get_body_preview(msg),
    }


# ─── Public API (green permission) ──────────────────────────────────────────

def list_unread_emails(account: str = "gmail", limit: int = 10, bypass_last_seen: bool = False) -> list[dict[str, Any]]:
    """
    List the latest unread emails from INBOX.
    Read-only operation — green permission.
    """
    conn = _connect(account)
    if not conn:
        return [{"error": f"IMAP credentials not configured or connection failed for account '{account}'."}]

    try:
        conn.select("INBOX", readonly=True)
        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            return [{"error": f"Failed to search for unread emails in {account}."}]

        msg_ids = data[0].split()
        if not msg_ids:
            return []

        if not bypass_last_seen:
            # Filter messages by last_seen_uid
            from backend.app.storage.db import get_last_seen_uid, update_last_seen_uid
            last_seen = get_last_seen_uid(account)

            new_msg_ids = [mid for mid in msg_ids if int(mid) > last_seen]

            if not new_msg_ids:
                return []

            # Update last seen to the highest sequence number we found
            highest_id = max([int(mid) for mid in new_msg_ids])
            update_last_seen_uid(account, highest_id)
            target_ids = new_msg_ids
        else:
            target_ids = msg_ids

        # Take the latest N emails
        target_ids = target_ids[-limit:]
        results: list[dict[str, Any]] = []

        for mid in reversed(target_ids):
            status, msg_data = conn.fetch(mid, "(BODY.PEEK[])")
            if status == "OK" and msg_data and msg_data[0]:
                raw = msg_data[0][1]
                if isinstance(raw, bytes):
                    results.append(_parse_email(raw))

        return results
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass


def search_emails(query: str, account: str = "gmail", limit: int = 10) -> list[dict[str, Any]]:
    """
    Search emails in INBOX by keyword in the subject.
    Read-only operation — green permission.
    """
    conn = _connect(account)
    if not conn:
        return [{"error": f"IMAP credentials not configured or connection failed for account '{account}'."}]

    try:
        conn.select("INBOX", readonly=True)
        # IMAP SEARCH by subject
        # Note: Some IMAP servers (like Gmail) might need charset specification, but SUBJECT usually works with ASCII.
        status, data = conn.search(None, f'(SUBJECT "{query}")')
        if status != "OK":
            return [{"error": f"Failed to search emails in {account}."}]

        msg_ids = data[0].split()
        if not msg_ids:
            return []

        msg_ids = msg_ids[-limit:]
        results: list[dict[str, Any]] = []

        for mid in reversed(msg_ids):
            status, msg_data = conn.fetch(mid, "(BODY.PEEK[])")
            if status == "OK" and msg_data and msg_data[0]:
                raw = msg_data[0][1]
                if isinstance(raw, bytes):
                    results.append(_parse_email(raw))

        return results
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        try:
            conn.close()
            conn.logout()
        except Exception:
            pass

def send_email(to: str, subject: str, body: str, account: str = "gmail") -> dict[str, Any]:
    """
    Send an email via SMTP.
    Requires red permission.
    """
    config = _get_account_config(account)
    if not config or not config["user"] or not config["pwd"]:
        return {"error": f"SMTP credentials not configured for account '{account}'."}

    msg = MIMEMultipart()
    msg["From"] = config["user"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        # Check port to decide between SSL (465) or STARTTLS (587)
        if config["smtp_port"] == 465:
            server = smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"])
            server.login(config["user"], config["pwd"])
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"])
            server.starttls()
            server.login(config["user"], config["pwd"])
            
        server.send_message(msg)
        server.quit()
        return {"status": "success", "message": f"Email sent to {to}"}
    except Exception as e:
        return {"error": f"Failed to send email: {str(e)}"}
