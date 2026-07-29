import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, date, timedelta
from backend.app.connectors.caldav_connector import list_events
from backend.app.connectors.mail_connector import list_unread_emails
from backend.app.agent.llm_client import chat_with_ollama
from backend.app.audit.audit_log import log_action
from backend.app.notifications.telegram_notifier import send_notification

# Setup rotating logger for summaries.log
summary_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs", "summaries.log")
os.makedirs(os.path.dirname(summary_path), exist_ok=True)

summary_logger = logging.getLogger("home_agent_summaries")
summary_logger.setLevel(logging.INFO)
if not summary_logger.handlers:
    # Use raw message format without prefixing log metadata (keeps the summaries clean)
    formatter = logging.Formatter("%(message)s")
    handler = RotatingFileHandler(
        summary_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    handler.setFormatter(formatter)
    summary_logger.addHandler(handler)

async def morning_summary():
    """
    Generates a morning summary of today's calendar events and unread emails,
    then sends it via Telegram.
    """
    log_action("morning_summary", "STARTED", "Executing scheduled morning summary task.")
    
    # 1. Fetch Calendar Events for Today
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # Convert to YYYY-MM-DD
    start_date = today.strftime("%Y-%m-%d")
    end_date = tomorrow.strftime("%Y-%m-%d")
    
    events = list_events(start_date=start_date, end_date=end_date)
    if isinstance(events, dict) and events.get("status") == "error":
        events = []

    # 2. Fetch Unread Emails
    emails = list_unread_emails(limit=10)
    if isinstance(emails, dict) and emails.get("status") == "error":
        emails = []

    # 3. Build Prompt for LLM
    events_text = "\n".join([f"- {e.get('summary', 'No Title')} ({e.get('start', '')} to {e.get('end', '')})" for e in events]) if events else "Нет событий на сегодня."
    emails_text = "\n".join([f"- От: {m.get('from', 'Unknown')} | Тема: {m.get('subject', 'No Subject')}" for m in emails]) if emails else "Нет непрочитанных писем."

    prompt = (
        f"Ты — дружелюбный домашний ассистент. Сегодня {today.strftime('%Y-%m-%d')}.\n\n"
        f"Вот список событий на сегодня из календаря:\n{events_text}\n\n"
        f"Вот список непрочитанных писем в почте:\n{emails_text}\n\n"
        f"Составь короткую, емкую и полезную утреннюю сводку для пользователя на русском языке. "
        f"Поприветствуй его, выдели самые важные дела из календаря и новые письма, на которые стоит обратить внимание. "
        f"Пиши в дружелюбном, уважительном тоне, без лишней «воды»."
    )

    # 4. Generate Summary
    try:
        response = await chat_with_ollama([{"role": "user", "content": prompt}], tools=[])
        response_text = response.get("message", {}).get("content", "Пустой ответ от ИИ.")
    except Exception as e:
        response_text = f"Произошла ошибка при генерации сводки: {e}"

    # 5. Log Summary with Rotation
    log_action("morning_summary", "GENERATED", "Summary generated successfully.")
    summary_logger.info(f"=== Summary for {today.strftime('%Y-%m-%d')} ===\n{response_text}\n\n")

    # 6. Send via Telegram
    result = await send_notification(response_text)
    if isinstance(result, dict) and result.get("status") == "dry_run":
        log_action("morning_summary", "DRY_RUN", "Telegram notification blocked by dry-run mode.")
    elif result:
        log_action("morning_summary", "SENT", "Telegram notification sent.")
    else:
        log_action("morning_summary", "FAILED_SEND", "Failed to send Telegram notification.")
