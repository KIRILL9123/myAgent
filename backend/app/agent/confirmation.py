import json
import asyncio
from typing import Any
from backend.app.storage import db
from backend.app.audit.audit_log import log_action


async def confirm_callback(nonce: str, chat_id: str, action_id: int | None = None) -> dict[str, Any]:
    session_id = f"telegram_{chat_id}"
    pending = db.find_pending_by_nonce(
        nonce,
        chat_id=str(chat_id),
        source_channel="telegram",
        action_id=action_id,
        session_id=session_id,
    )
    if not pending:
        return {"status": "error", "code": "not_found",
                "message": "Action not found, expired, or not authorized."}

    claimed = db.claim_pending_action(
        pending["id"], nonce, chat_id=str(chat_id),
        source_channel="telegram", session_id=session_id,
    )
    if not claimed:
        return {"status": "error", "code": "already_processed",
                "message": "Action already claimed or expired."}
    return await _execute_claimed(claimed)


async def cancel_callback(nonce: str, chat_id: str, action_id: int | None = None) -> dict[str, Any]:
    session_id = f"telegram_{chat_id}"
    pending = db.find_pending_by_nonce(
        nonce,
        chat_id=str(chat_id),
        source_channel="telegram",
        action_id=action_id,
        session_id=session_id,
    )
    if not pending:
        return {"status": "error", "code": "not_found",
                "message": "Action not found."}
    cancelled = db.cancel_pending_action(
        pending["id"], nonce, source_channel="telegram",
        chat_id=str(chat_id), session_id=session_id,
    )
    if not cancelled:
        return {"status": "error", "code": "already_processed",
                "message": "Action already claimed, cancelled, or expired."}
    log_action(pending["action"], "CANCELLED", f"Callback cancel action={pending['id']}")
    return {"status": "ok", "code": "cancelled", "action": pending["action"],
            "message": f"Action '{pending['action']}' cancelled."}


async def _execute_claimed(claimed: dict[str, Any]) -> dict[str, Any]:
    from backend.app.agent.orchestrator import _dispatch_tool, sanitize_tool_result
    action_name = claimed["action"]
    args = claimed["args"]

    log_action(action_name, "CONFIRMED", f"Executing id={claimed['id']}")
    try:
        result = await asyncio.to_thread(_dispatch_tool, action_name, args)
        result = sanitize_tool_result(action_name, result)
        if isinstance(result, dict) and result.get("status") == "error":
            err = result.get("message", "Unknown error")
            db.finalize_pending_action(
                claimed["id"], "failed", err,
                source_channel=claimed.get("source_channel", "telegram"),
                chat_id=str(claimed.get("chat_id", "")),
                session_id=claimed.get("session_id"),
            )
            log_action(action_name, "ERROR", err)
            return {"status": "error", "code": "execution_failed",
                    "message": f"Action failed: {err}", "action": action_name}
        db.finalize_pending_action(
            claimed["id"], "completed",
            source_channel=claimed.get("source_channel", "telegram"),
            chat_id=str(claimed.get("chat_id", "")),
            session_id=claimed.get("session_id"),
        )
        log_action(action_name, "EXECUTED", str(result)[:200])
        if claimed.get("session_id"):
            db.save_message(claimed["session_id"], "tool",
                            content=json.dumps(result, ensure_ascii=False),
                            name=action_name)
        return {"status": "ok", "code": "completed", "action": action_name,
                "result": result, "message": f"Action '{action_name}' completed."}
    except Exception as e:
        db.finalize_pending_action(
            claimed["id"], "failed", str(e)[:200],
            source_channel=claimed.get("source_channel", "telegram"),
            chat_id=str(claimed.get("chat_id", "")),
            session_id=claimed.get("session_id"),
        )
        log_action(action_name, "ERROR", str(e)[:200])
        return {"status": "error", "code": "execution_failed",
                "message": f"Action failed: {type(e).__name__}", "action": action_name}
