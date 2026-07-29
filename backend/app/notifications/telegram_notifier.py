import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_notification(message: str, chat_id: str = None) -> bool | dict:
    """
    Sends a message via the Telegram Bot API.
    Returns True/False in REAL mode, or {"status":"dry_run","would_do":{...}} in DRY_RUN mode.
    """
    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run():
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
