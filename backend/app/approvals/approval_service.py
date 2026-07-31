import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.storage.db import get_db_connection


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _loads(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value) if value else {}
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "id", "kind", "source_id", "title", "summary", "payload",
        "source_channel", "status", "resolution_note", "created_at",
        "updated_at", "resolved_at",
    )
    result = dict(zip(keys, row))
    result["payload"] = _loads(result.get("payload"))
    return result


def _upsert_request(kind: str, source_id: str, title: str, summary: str,
                    payload: dict[str, Any], source_channel: str = "web") -> str:
    now = _now()
    request_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO approval_requests
               (id, kind, source_id, title, summary, payload_json, source_channel,
                status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
               ON CONFLICT(kind, source_id) DO UPDATE SET
                 title=excluded.title,
                 summary=excluded.summary,
                 payload_json=excluded.payload_json,
                 source_channel=excluded.source_channel,
                 updated_at=excluded.updated_at
               WHERE approval_requests.status = 'PENDING'""",
            (request_id, kind, source_id, title, summary, _json(payload),
             source_channel, now, now),
        )
        row = conn.execute(
            "SELECT id FROM approval_requests WHERE kind = ? AND source_id = ?",
            (kind, source_id),
        ).fetchone()
        conn.commit()
    return str(row[0]) if row else request_id


def create_sandbox_apply_request(plan: dict[str, Any], source_channel: str = "web") -> dict[str, Any]:
    session_id = str(plan.get("session_id", ""))
    source_id = f"{session_id}:{plan.get('baseline_at', '')}:{plan.get('workspace_digest', '')[:24]}"
    approval_id = _upsert_request(
        "SANDBOX_APPLY",
        source_id,
        "Применить изменения из песочницы",
        f"Изменения файлов: {plan.get('summary', {}).get('changed_files', 0)}. Перед применением будет проверен конфликт с основным проектом.",
        {"sandbox_plan": plan},
        source_channel,
    )
    return {
        "status": "pending_approval",
        "approval_id": approval_id,
        "kind": "SANDBOX_APPLY",
        "session_id": session_id,
        "summary": plan.get("summary", {}),
        "message": "Запрос на применение создан. Подтвердите его в Центре подтверждений.",
    }


def _reconcile_resolved() -> None:
    """Keep the projection accurate when a legacy domain UI resolves an item."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, kind, source_id FROM approval_requests
               WHERE status = 'PENDING'"""
        ).fetchall()
        now = _now()
        for approval_id, kind, source_id in rows:
            resolved_status: str | None = None
            if kind == "FACT":
                source = conn.execute(
                    "SELECT status FROM user_facts WHERE id = ?", (int(source_id),)
                ).fetchone()
                if source and source[0] != "pending_approval":
                    resolved_status = "APPROVED" if source[0] == "approved" else "REJECTED"
            elif kind == "COMMITMENT":
                source = conn.execute(
                    "SELECT status FROM commitments WHERE id = ?", (source_id,)
                ).fetchone()
                if source and source[0] != "PROPOSED":
                    resolved_status = "APPROVED" if source[0] == "ACTIVE" else "REJECTED"
            elif kind == "SUBSCRIPTION":
                source = conn.execute(
                    "SELECT status FROM subscriptions WHERE id = ?", (source_id,)
                ).fetchone()
                if source and source[0] != "PROPOSED":
                    resolved_status = "APPROVED" if source[0] == "ACTIVE" else "REJECTED"
            elif kind == "ACTION":
                source = conn.execute(
                    "SELECT status FROM pending_actions WHERE rowid = ?", (int(source_id),)
                ).fetchone()
                if not source:
                    resolved_status = None
                elif source[0] == "cancelled":
                    resolved_status = "REJECTED"
                elif source[0] == "completed":
                    resolved_status = "APPROVED"
                elif source[0] in {"executing", "executed"}:
                    resolved_status = "APPROVED"
                elif source[0] != "pending":
                    resolved_status = "REJECTED"
            elif kind == "SKILL":
                source = conn.execute(
                    "SELECT status FROM procedural_skills WHERE id = ?", (int(source_id),)
                ).fetchone()
                if source and source[0] != "draft":
                    resolved_status = "APPROVED" if source[0] == "approved" else "REJECTED"
            if resolved_status:
                conn.execute(
                    """UPDATE approval_requests
                       SET status = ?, updated_at = ?, resolved_at = COALESCE(resolved_at, ?)
                       WHERE id = ? AND status = 'PENDING'""",
                    (resolved_status, now, now, approval_id),
                )
        conn.commit()


def sync_pending_approvals() -> None:
    """Project existing domain-specific pending records into one approval inbox."""
    with get_db_connection() as conn:
        facts = conn.execute(
            """SELECT id, content, category, confidence, source_type, created_at
               FROM user_facts WHERE status = 'pending_approval'"""
        ).fetchall()
        commitments = conn.execute(
            """SELECT id, title, description, confidence, source_type, deadline_at, created_at
               FROM commitments WHERE status = 'PROPOSED'"""
        ).fetchall()
        subscriptions = conn.execute(
            """SELECT id, name, provider, subscription_type, amount, currency,
                      trial_ends_at, next_charge_at, confidence, source_type, created_at
               FROM subscriptions WHERE status = 'PROPOSED'"""
        ).fetchall()
        actions = conn.execute(
            """SELECT rowid, session_id, action_name, args, source_channel, created_at
               FROM pending_actions WHERE status = 'pending'"""
        ).fetchall()
        skills = conn.execute(
            """SELECT id, name, description, category, created_at
               FROM procedural_skills WHERE status = 'draft'"""
        ).fetchall()

    for fact_id, content, category, confidence, source_type, created_at in facts:
        _upsert_request(
            "FACT", str(fact_id), "Подтвердить факт памяти", content,
            {"fact_id": fact_id, "content": content, "category": category,
             "confidence": confidence, "source_type": source_type, "created_at": created_at},
        )
    for commitment_id, title, description, confidence, source_type, deadline_at, created_at in commitments:
        summary = description or "Предложение обязательства требует подтверждения."
        _upsert_request(
            "COMMITMENT", commitment_id, "Подтвердить обязательство", title,
            {"commitment_id": commitment_id, "description": description,
             "confidence": confidence, "source_type": source_type,
             "deadline_at": deadline_at, "created_at": created_at},
        )
    for subscription_id, name, provider, subscription_type, amount, currency, trial_ends_at, next_charge_at, confidence, source_type, created_at in subscriptions:
        price = f"{amount:g} {currency or ''}".strip() if amount is not None else "сумма не указана"
        summary = f"{provider or name} · {subscription_type} · {price}"
        _upsert_request(
            "SUBSCRIPTION", subscription_id, "Проверить подписку", summary,
            {"subscription_id": subscription_id, "name": name, "provider": provider,
             "subscription_type": subscription_type, "amount": amount, "currency": currency,
             "trial_ends_at": trial_ends_at, "next_charge_at": next_charge_at,
             "confidence": confidence, "source_type": source_type, "created_at": created_at},
        )
    for action_id, session_id, action_name, args_json, source_channel, created_at in actions:
        args = _loads(args_json)
        _upsert_request(
            "ACTION", str(action_id), f"Подтвердить действие: {action_name}",
            json.dumps(args, ensure_ascii=False),
            {"action_id": action_id, "session_id": session_id, "action_name": action_name, "args": args,
             "created_at": created_at}, source_channel or "web",
        )
    for skill_id, name, description, category, created_at in skills:
        _upsert_request(
            "SKILL", str(skill_id), f"Подтвердить навык: {name}",
            description or "Новый процедурный навык требует подтверждения.",
            {"skill_id": skill_id, "name": name, "category": category, "created_at": created_at},
        )
    _reconcile_resolved()


def list_approvals(status: str = "PENDING") -> list[dict[str, Any]]:
    sync_pending_approvals()
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, kind, source_id, title, summary, payload_json,
                      source_channel, status, resolution_note, created_at,
                      updated_at, resolved_at
               FROM approval_requests WHERE status = ?
               ORDER BY created_at DESC""",
            (status.upper(),),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _get_pending(approval_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT id, kind, source_id, title, summary, payload_json,
                      source_channel, status, resolution_note, created_at,
                      updated_at, resolved_at
               FROM approval_requests WHERE id = ? AND status = 'PENDING'""",
            (approval_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


async def resolve_approval(approval_id: str, decision: str,
                           note: str | None = None) -> dict[str, Any]:
    request = _get_pending(approval_id)
    if not request:
        raise ValueError("approval request not found or already resolved")
    decision = decision.lower()
    if decision not in {"approve", "reject"}:
        raise ValueError("decision must be approve or reject")

    kind = request["kind"]
    source_id = request["source_id"]
    if decision == "reject":
        if kind == "FACT":
            from backend.app.memory.memory_service import reject_fact
            if not reject_fact(int(source_id)):
                raise ValueError("fact is no longer pending")
        elif kind == "COMMITMENT":
            from backend.app.commitments.commitment_service import transition_commitment
            transition_commitment(source_id, "cancel", {"source": "approval_center", "note": note})
        elif kind == "SUBSCRIPTION":
            from backend.app.subscriptions.subscription_service import transition_subscription
            transition_subscription(source_id, "cancel", {"source": "approval_center", "note": note})
        elif kind == "ACTION":
            from backend.app.storage.db import get_pending_action, delete_pending_action
            action = get_pending_action(request["payload"].get("session_id", ""))
            if action:
                delete_pending_action(action["session_id"])
        elif kind == "SANDBOX_APPLY":
            pass
        elif kind == "SKILL":
            from backend.app.memory.skill_service import disable_skill
            if not disable_skill(int(source_id)):
                raise ValueError("skill is no longer pending")
        status = "REJECTED"
    else:
        if kind == "FACT":
            from backend.app.memory.memory_service import approve_fact
            if not await approve_fact(int(source_id)):
                raise ValueError("fact is no longer pending")
        elif kind == "COMMITMENT":
            from backend.app.commitments.commitment_service import transition_commitment
            transition_commitment(source_id, "approve", {"source": "approval_center", "note": note})
        elif kind == "SUBSCRIPTION":
            from backend.app.subscriptions.subscription_service import transition_subscription
            transition_subscription(source_id, "approve", {"source": "approval_center", "note": note})
        elif kind == "ACTION":
            from backend.app.agent.orchestrator import _dispatch_tool, sanitize_tool_result
            from backend.app.storage.db import claim_pending_action, finalize_pending_action, get_pending_action
            payload = request["payload"]
            session_id = payload.get("session_id", "")
            action = get_pending_action(session_id)
            if not action:
                raise ValueError("action is no longer pending")
            claimed = claim_pending_action(action["id"], action["nonce_hash"], action.get("chat_id", ""))
            if not claimed:
                raise ValueError("action could not be claimed")
            result = await asyncio.to_thread(_dispatch_tool, action["action"], action["args"])
            result = sanitize_tool_result(action["action"], result)
            if isinstance(result, dict) and result.get("status") == "error":
                finalize_pending_action(action["id"], "failed", result.get("message", ""))
                raise ValueError(result.get("message", "action failed"))
            finalize_pending_action(action["id"], "executed")
        elif kind == "SANDBOX_APPLY":
            from backend.app.sandbox_service import SandboxError, apply_sandbox_plan
            plan = request["payload"].get("sandbox_plan")
            if not isinstance(plan, dict):
                raise ValueError("sandbox apply plan is missing")
            try:
                await asyncio.to_thread(apply_sandbox_plan, plan, operation_id=approval_id)
            except SandboxError as exc:
                raise ValueError(str(exc)) from exc
        elif kind == "SKILL":
            from backend.app.memory.skill_service import approve_skill
            if not approve_skill(int(source_id)):
                raise ValueError("skill is no longer pending")
        status = "APPROVED"

    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            """UPDATE approval_requests SET status = ?, resolution_note = ?,
                      updated_at = ?, resolved_at = ?
               WHERE id = ? AND status = 'PENDING'""",
            (status, note, now, now, approval_id),
        )
        conn.commit()
    return {**request, "status": status, "resolution_note": note, "resolved_at": now}
