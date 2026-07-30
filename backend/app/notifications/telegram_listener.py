import os
import asyncio
import json
import httpx
from dotenv import load_dotenv
from backend.app.audit.audit_log import log_action
from backend.app.agent.orchestrator import run_orchestrator
from backend.app.notifications.telegram_notifier import (
    send_notification, send_inline_keyboard, edit_message, answer_callback,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def process_message(chat_id: str, text: str):
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        log_action("UNAUTHORIZED_TELEGRAM_ACCESS", "REJECTED", f"Attempt from chat_id: {chat_id}, text: {text}")
        return

    session_id = f"telegram_{chat_id}"

    try:
        result = await run_orchestrator(text, session_id=session_id)
        response_text = result.get("response", "")
        requires_confirmation = result.get("requires_confirmation", False)

        if requires_confirmation:
            nonce = result.get("pending_nonce")
            action_id = result.get("pending_action_id")
            if nonce and action_id:
                buttons = [[
                    {"text": "✅ Подтвердить", "callback_data": f"confirm:{nonce}:{action_id}"},
                    {"text": "❌ Отмена", "callback_data": f"cancel:{nonce}:{action_id}"},
                ]]
                sent = await send_inline_keyboard(str(chat_id), response_text, buttons)
                if sent and sent.get("message_id"):
                    from backend.app.storage.db import get_db_connection
                    with get_db_connection() as conn:
                        conn.execute(
                            "UPDATE pending_actions SET telegram_message_id=? WHERE rowid=?",
                            (sent["message_id"], action_id)
                        )
                        conn.commit()
            else:
                response_text += "\n\n⚠️ Это действие требует подтверждения. Ответьте 'да' или 'нет'."
                await send_notification(response_text, chat_id=str(chat_id))
        elif response_text:
            await send_notification(response_text, chat_id=str(chat_id))

    except Exception as e:
        print(f"[TELEGRAM_LISTENER] Error processing message: {e}")
        await send_notification("Произошла ошибка при обработке запроса.", chat_id=str(chat_id))


async def process_callback_query(callback: dict):
    cb_id = callback.get("id")
    data = callback.get("data", "")
    msg = callback.get("message", {})
    chat = msg.get("chat", {})
    chat_id = str(chat.get("id"))
    message_id = msg.get("message_id")

    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        await answer_callback(cb_id, "Not authorized")
        return

    parts = data.split(":", 2)
    if len(parts) != 3:
        await answer_callback(cb_id, "Invalid request")
        return

    action, nonce, action_id = parts
    from backend.app.agent.confirmation import confirm_callback, cancel_callback

    if action == "confirm":
        result = await confirm_callback(nonce, chat_id)
    elif action == "cancel":
        result = await cancel_callback(nonce, chat_id)
    else:
        await answer_callback(cb_id, "Unknown action")
        return

    await answer_callback(cb_id, result.get("message", "Done"))
    if message_id:
        status_icon = "✅" if result.get("status") == "ok" else "❌"
        await edit_message(chat_id, message_id, f"{status_icon} {result.get('message', 'Done')}")

async def process_voice_message(chat_id: str, file_id: str):
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        log_action("UNAUTHORIZED_TELEGRAM_ACCESS", "REJECTED", f"Voice attempt from chat_id: {chat_id}")
        return
        
    try:
        await send_notification("Слушаю ваше голосовое сообщение...", chat_id=str(chat_id))
        
        async with httpx.AsyncClient() as client:
            # 1. Get file path
            file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
            file_resp = await client.get(file_url)
            file_resp.raise_for_status()
            file_path = file_resp.json()["result"]["file_path"]
            
            # 2. Download file
            download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            dl_resp = await client.get(download_url)
            dl_resp.raise_for_status()
            
            # save to temp file
            import tempfile
            import os
            from backend.app.voice.transcriber import transcribe_audio
            
            fd, temp_path = tempfile.mkstemp(suffix=".ogg")
            with os.fdopen(fd, 'wb') as f:
                f.write(dl_resp.content)
            
            # 3. Transcribe
            # Running transcriber in a thread because it's CPU bound and blocks asyncio loop
            text = await asyncio.to_thread(transcribe_audio, temp_path)
            
            # cleanup
            try:
                os.remove(temp_path)
            except Exception:
                pass
                
            if not text:
                await send_notification("Не удалось распознать текст.", chat_id=str(chat_id))
                return
                
            # 4. Confirm and process
            await send_notification(f"Я услышал: '{text}'", chat_id=str(chat_id))
            await process_message(chat_id, text)
            
    except Exception as e:
        print(f"[TELEGRAM_LISTENER] Error processing voice: {e}")
        await send_notification(f"Ошибка при обработке голосового сообщения: {e}", chat_id=str(chat_id))

async def start_polling():
    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM_LISTENER] TELEGRAM_BOT_TOKEN not configured, polling disabled.")
        return

    offset = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    print("[TELEGRAM_LISTENER] Started long-polling.")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                # Use long polling (timeout 50 seconds on Telegram side)
                payload = {"offset": offset, "timeout": 50}
                response = await client.get(url, params=payload)
                response.raise_for_status()
                data = response.json()
                
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1

                        if "callback_query" in update:
                            asyncio.create_task(process_callback_query(update["callback_query"]))
                        elif "message" in update:
                            chat_id = str(update["message"]["chat"]["id"])

                            if "text" in update["message"]:
                                text = update["message"]["text"]
                                asyncio.create_task(process_message(chat_id, text))
                            elif "voice" in update["message"]:
                                file_id = update["message"]["voice"]["file_id"]
                                asyncio.create_task(process_voice_message(chat_id, file_id))
                            
            except httpx.ReadTimeout:
                # Normal for long polling
                pass
            except asyncio.CancelledError:
                print("[TELEGRAM_LISTENER] Stopping long-polling.")
                break
            except Exception as e:
                print(f"[TELEGRAM_LISTENER] Error fetching updates: {e}")
                await asyncio.sleep(5)
                
            await asyncio.sleep(1) # Small delay to prevent tight loop in case of errors

