import os
import json
from datetime import datetime, date, timedelta
from backend.app.connectors.caldav_connector import list_events
from backend.app.connectors.mail_connector import list_unread_emails
from backend.app.agent.llm_client import chat_with_ollama
from backend.app.audit.audit_log import log_action
from backend.app.notifications.telegram_notifier import send_notification

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
    
    events_raw = list_events(start_date=start_date, end_date=end_date)
    # the function returns a JSON string, need to load it
    try:
        events = json.loads(events_raw)
    except Exception:
        events = [{"error": "Failed to parse events"}]
        
    # 2. Fetch Unread Emails (Gmail)
    try:
        emails = list_unread_emails(account="gmail", limit=5)
    except Exception as e:
        emails = [{"error": str(e)}]
        
    # 2.5 Fetch Countdowns
    from backend.app.countdown.countdown_service import get_all_countdowns
    countdowns = get_all_countdowns().get("countdowns", [])
    countdowns_str = "Дедлайнов нет."
    if countdowns:
        c_list = []
        for c in countdowns:
            mark = "🚨 ВАЖНО " if c["days_remaining"] < 30 else ""
            c_list.append(f"- {mark}{c['title']} ({c['target_date']}): осталось дней - {c['days_remaining']}")
        countdowns_str = "\n".join(c_list)
        
    # 3. Build Prompt for LLM
    prompt = f"""
Ты — персональный ИИ-ассистент. Составь утреннюю сводку для пользователя на {today.strftime("%d.%m.%Y")}.
Используй только русский язык. Сделай сводку дружелюбной, структурированной и краткой.
Выдели важные события и письма. Если до дедлайна осталось менее 30 дней, обязательно обрати на это внимание.

=== Дедлайны ===
{countdowns_str}

=== Календарь на сегодня ===
{json.dumps(events, ensure_ascii=False, indent=2)}

=== Последние непрочитанные письма (Gmail) ===
{json.dumps(emails, ensure_ascii=False, indent=2)}
"""

    # 4. Generate Summary
    try:
        response = await chat_with_ollama([{"role": "user", "content": prompt}], tools=[])
        response_text = response.get("message", {}).get("content", "Пустой ответ от ИИ.")
    except Exception as e:
        response_text = f"Произошла ошибка при генерации сводки: {e}"

    # 5. Log Summary
    log_action("morning_summary", "GENERATED", "Summary generated successfully.")
    
    summary_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs", "summaries.log")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(f"=== Summary for {today.strftime('%Y-%m-%d')} ===\n{response_text}\n\n")

    # 6. Send via Telegram
    success = await send_notification(response_text)
    if success:
        log_action("morning_summary", "SENT", "Telegram notification sent.")
    else:
        log_action("morning_summary", "FAILED_SEND", "Failed to send Telegram notification.")
