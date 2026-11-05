import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def telegram_writes_allowed() -> bool:
    """Allow Telegram delivery independently from other dry-run integrations."""
    from backend.app.core.execution_mode import is_dry_run
    return not is_dry_run() or os.getenv("TELEGRAM_ALLOW_NOTIFICATIONS", "false").strip().lower() in {"1", "true", "yes", "on"}

async def send_notification(message: str, chat_id: str = None) -> bool | dict:
    """
    Sends a message via the Telegram Bot API.
    Returns True/False in REAL mode, or {"status":"dry_run","would_do":{...}} in DRY_RUN mode.
    """
    if not telegram_writes_allowed():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "send_notification",
                "message": message,
                "chat_id": chat_id or TELEGRAM_CHAT_ID,
            },
        }

    target_chat_id = chat_id or TELEGRAM_CHAT_ID
    
    if not TELEGRAM_BOT_TOKEN or not target_chat_id:
        print("[NOTIFIER] Telegram credentials not configured.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": message
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"[NOTIFIER] Failed to send Telegram notification: {e}")
        return False


async def send_inline_keyboard(chat_id: str, text: str, buttons: list[list[dict]]) -> dict | None:
    if not telegram_writes_allowed():
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": buttons},
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json().get("result")
    except Exception as e:
        print(f"[NOTIFIER] Failed to send inline keyboard: {e}")
        return None


async def edit_message(chat_id: str, message_id: int, text: str) -> bool:
    if not telegram_writes_allowed():
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"[NOTIFIER] Failed to edit message: {e}")
        return False


async def answer_callback(callback_id: str, text: str = "") -> bool:
    if not telegram_writes_allowed():
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id, "text": text}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"[NOTIFIER] Failed to answer callback: {e}")
        return False
