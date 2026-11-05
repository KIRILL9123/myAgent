import json
from datetime import date, datetime, timedelta
from typing import Any

from backend.app.commitments.commitment_service import list_commitments
from backend.app.conflicts.conflict_service import detect_conflicts
from backend.app.countdown.countdown_service import get_all_countdowns
from backend.app.calendar.calendar_service import list_events
from backend.app.finance.finance_service import get_summary
from backend.app.subscriptions.subscription_service import list_subscriptions
from backend.app.storage.db import get_db_connection
from backend.app.action_center_service import build_action_center
from backend.app.temporal.time_context import (
    TemporalContext,
    build_temporal_context,
    classify_due,
    parse_datetime,
)


def _alert(severity: str, signal_type: str, title: str, detail: str,
           due_at: str | None = None, target: str | None = None) -> dict[str, Any]:
    return {
        "severity": severity,
        "type": signal_type,
        "title": title,
        "detail": detail,
        "due_at": due_at,
        "target": target,
    }


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity, 4)


def _json(value: Any, default: Any) -> str:
    return json.dumps(default if value is None else value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def _calendar_signal(today: date, include_external: bool) -> dict[str, Any]:
    if not include_external:
        return {"status": "not_requested", "events": [], "error": None}
    result = list_events(today.isoformat(), (today + timedelta(days=1)).isoformat())
    if isinstance(result, dict):
        return {"status": "error", "events": [], "error": result.get("message", "calendar unavailable")}
    return {"status": "ok", "events": result, "error": None}


def _mail_signal(include_external: bool) -> dict[str, Any]:
    if not include_external:
        return {"status": "not_requested", "unread_count": 0, "accounts": [], "error": None}
    from backend.app.connectors.mail_connector import list_unread_emails

    accounts: list[dict[str, Any]] = []
    total = 0
    for account in ("gmail", "ukrnet"):
        result = list_unread_emails(account, limit=20, bypass_last_seen=True)
        if isinstance(result, dict) and result.get("status") == "error":
            accounts.append({"account": account, "status": "error", "unread_count": 0,
                             "error": result.get("message", "mail unavailable")})
            continue
        count = len(result)
        total += count
        accounts.append({"account": account, "status": "ok", "unread_count": count, "error": None})
    errors = [item["error"] for item in accounts if item.get("error")]
    return {"status": "error" if errors and total == 0 else "ok", "unread_count": total,
            "accounts": accounts, "error": "; ".join(errors) if errors else None}


def build_state_snapshot(reference_time: datetime | None = None,
                         include_external: bool = True,
                         *,
                         timezone_name: str | None = None,
                         temporal_context: TemporalContext | None = None) -> dict[str, Any]:
    """Aggregate current personal signals into a deterministic, read-only snapshot."""
    if temporal_context is not None and reference_time is not None:
        raise ValueError("provide either reference_time or temporal_context")
    context = temporal_context or build_temporal_context(reference_time, timezone_name)
    now = context.now_utc
    today = context.today
    commitments = list_commitments(include_completed=False)
    subscriptions = list_subscriptions()
    countdown_result = get_all_countdowns(temporal_context=context)
    countdowns = countdown_result.get("countdowns", []) if isinstance(countdown_result, dict) else []
    month_start = today.replace(day=1).isoformat()
    month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    finance = get_summary(month_start, month_end.isoformat())
    calendar = _calendar_signal(today, include_external)
    mail = _mail_signal(include_external)
    conflicts = detect_conflicts(
        temporal_context=context,
        horizon_days=30,
        include_external=include_external,
    )

    alerts: list[dict[str, Any]] = []
    for conflict in conflicts.get("conflicts", []):
        alerts.append(_alert(
            conflict.get("priority", "high"),
            "conflict",
            conflict["title"],
            conflict["summary"],
            conflict.get("due_at") or conflict.get("event_start"),
            "/calendar",
        ))
    for item in commitments:
        if item.get("status") != "ACTIVE":
            continue
        due = classify_due(item.get("deadline_at"), context, 2)
        if not due.attention:
            continue
        if due.status == "overdue":
            alerts.append(_alert("critical", "commitment", f"Просрочено: {item['title']}",
                                 "Обязательство требует пересмотра.", item.get("deadline_at"), "/commitments"))
        elif due.status in {"due_today", "upcoming"}:
            alerts.append(_alert("high", "commitment", f"Скоро срок: {item['title']}",
                                 "Срок наступает в ближайшие два дня.", item.get("deadline_at"), "/commitments"))

    for item in subscriptions:
        if item.get("status") != "ACTIVE":
            continue
        event_at = item.get("next_charge_at") or item.get("trial_ends_at")
        due = classify_due(event_at, context, 7)
        if not due.attention:
            continue
        if due.status == "overdue":
            alerts.append(_alert("critical", "subscription", f"Проверьте подписку: {item['name']}",
                                 "Дата списания или окончания trial уже прошла.", event_at, "/subscriptions"))
        elif due.status in {"due_today", "upcoming"}:
            kind = "списание" if item.get("next_charge_at") else "окончание trial"
            alerts.append(_alert("high", "subscription", f"Скоро {kind}: {item['name']}",
                                 "Проверьте, нужно ли продолжать подписку.", event_at, "/subscriptions"))

    for item in countdowns:
        days = item.get("days_remaining")
        if not isinstance(days, int):
            continue
        if days < 0:
            alerts.append(_alert("critical", "deadline", f"Просрочен дедлайн: {item['title']}",
                                 "Дедлайн нужно закрыть или обновить.", item.get("target_date"), "/deadlines"))
        elif days <= 7:
            alerts.append(_alert("high", "deadline", f"Дедлайн через {days} дн.: {item['title']}",
                                 "Подготовьте следующее действие.", item.get("target_date"), "/deadlines"))

    proposed_commitments = [item for item in commitments if item.get("status") == "PROPOSED"]
    proposed_subscriptions = [item for item in subscriptions if item.get("status") == "PROPOSED"]
    if proposed_commitments or proposed_subscriptions:
        total = len(proposed_commitments) + len(proposed_subscriptions)
        approval_target = "/subscriptions" if proposed_subscriptions else "/approvals"
        alerts.append(_alert("medium", "approval", f"Новых предложений на проверку: {total}",
                             "Подтвердите или отклоните найденные данные.", target=approval_target))

    if mail.get("unread_count", 0) > 0:
        alerts.append(_alert("low", "mail", f"Непрочитанных писем: {mail['unread_count']}",
                             "Проверьте важные входящие сообщения.", target="/mail"))

    alerts.sort(key=lambda item: (_severity_rank(item["severity"]), item.get("due_at") or "9999"))
    critical_count = sum(item["severity"] == "critical" for item in alerts)
    if critical_count:
        health = "attention"
        headline = "Есть просроченные или критичные сигналы"
    elif alerts:
        health = "watch"
        headline = "Есть ближайшие дела, требующие внимания"
    else:
        health = "clear"
        headline = "Критичных сигналов нет"

    active_commitments = [item for item in commitments if item.get("status") == "ACTIVE"]
    active_subscriptions = [item for item in subscriptions if item.get("status") == "ACTIVE"]
    upcoming_deadlines = [item for item in countdowns if isinstance(item.get("days_remaining"), int) and 0 <= item["days_remaining"] <= 30]
    action_center = build_action_center(temporal_context=context, mode="attention", limit=5, include_external=False)
    return {
        "generated_at": now.isoformat(),
        "timezone": context.timezone_name,
        "today": today.isoformat(),
        "health": health,
        "headline": headline,
        "counts": {
            "active_commitments": len(active_commitments),
            "proposed_commitments": len(proposed_commitments),
            "active_subscriptions": len(active_subscriptions),
            "proposed_subscriptions": len(proposed_subscriptions),
            "deadlines_next_30_days": len(upcoming_deadlines),
            "calendar_events_today": len(calendar.get("events", [])),
            "unread_emails": mail.get("unread_count", 0),
            "alerts_total": len(alerts),
            "alerts_critical": critical_count,
            "conflicts": len(conflicts.get("conflicts", [])),
        },
        "alerts": alerts[:12],
        "next_actions": alerts[:5],
        "domains": {
            "commitments": [{"id": item["id"], "title": item["title"], "status": item["status"],
                             "deadline_at": item.get("deadline_at"), "owner": item.get("owner")} for item in commitments if item.get("status") in {"ACTIVE", "PROPOSED"}],
            "subscriptions": [{"id": item["id"], "name": item["name"], "status": item["status"],
                                "trial_ends_at": item.get("trial_ends_at"), "next_charge_at": item.get("next_charge_at"),
                                "amount": item.get("amount"), "currency": item.get("currency")} for item in subscriptions if item.get("status") in {"ACTIVE", "PROPOSED"}],
            "deadlines": upcoming_deadlines[:10],
            "calendar": calendar,
            "conflicts": conflicts,
            "finance": finance,
            "mail": mail,
        },
        "action_center": {
            "summary": action_center["summary"],
            "next_actions": action_center["actions"],
        },
    }


def persist_daily_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Upsert one snapshot for the local calendar day and return its metadata."""
    generated_at = parse_datetime(snapshot.get("generated_at")) or build_temporal_context().now_utc
    snapshot_context = build_temporal_context(generated_at, snapshot.get("timezone"))
    snapshot_date = snapshot_context.today.isoformat()
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO state_snapshots
               (snapshot_date, generated_at, health, headline, counts_json, alerts_json, snapshot_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(snapshot_date) DO UPDATE SET
                 generated_at=excluded.generated_at,
                 health=excluded.health,
                 headline=excluded.headline,
                 counts_json=excluded.counts_json,
                 alerts_json=excluded.alerts_json,
                 snapshot_json=excluded.snapshot_json""",
            (snapshot_date, snapshot.get("generated_at", generated_at.isoformat()),
             snapshot.get("health", "watch"), snapshot.get("headline", ""),
             _json(snapshot.get("counts"), {}), _json(snapshot.get("alerts"), []),
             _json(snapshot, {})),
        )
        conn.commit()
    return {"snapshot_date": snapshot_date, "generated_at": snapshot.get("generated_at"),
            "health": snapshot.get("health"), "headline": snapshot.get("headline"),
            "counts": snapshot.get("counts", {}), "alerts": snapshot.get("alerts", [])}


def capture_daily_snapshot(reference_time: datetime | None = None,
                           include_external: bool = True,
                           *,
                           timezone_name: str | None = None,
                           temporal_context: TemporalContext | None = None) -> dict[str, Any]:
    snapshot = build_state_snapshot(
        reference_time,
        include_external=include_external,
        timezone_name=timezone_name,
        temporal_context=temporal_context,
    )
    persist_daily_snapshot(snapshot)
    return snapshot


def get_state_history(
    days: int = 30,
    reference_time: datetime | None = None,
    *,
    timezone_name: str | None = None,
    temporal_context: TemporalContext | None = None,
) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 365))
    if temporal_context is not None and reference_time is not None:
        raise ValueError("provide either reference_time or temporal_context")
    context = temporal_context or build_temporal_context(reference_time, timezone_name)
    cutoff = (context.today - timedelta(days=days - 1)).isoformat()
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT snapshot_date, generated_at, health, headline, counts_json, alerts_json
               FROM state_snapshots WHERE snapshot_date >= ? ORDER BY snapshot_date DESC""",
            (cutoff,),
        ).fetchall()
    return [{"snapshot_date": row[0], "generated_at": row[1], "health": row[2],
             "headline": row[3], "counts": _loads(row[4], {}), "alerts": _loads(row[5], [])}
            for row in rows]


def build_state_report(reference_time: datetime | None = None,
                       include_external: bool = True,
                       history_days: int = 30,
                       *,
                       timezone_name: str | None = None,
                       temporal_context: TemporalContext | None = None) -> dict[str, Any]:
    """Return current state plus a compact trend and deterministic State of Me brief."""
    if temporal_context is not None and reference_time is not None:
        raise ValueError("provide either reference_time or temporal_context")
    context = temporal_context or build_temporal_context(reference_time, timezone_name)
    snapshot = capture_daily_snapshot(temporal_context=context, include_external=include_external)
    history = get_state_history(history_days, temporal_context=context)
    previous = next((item for item in history if item["snapshot_date"] != history[0]["snapshot_date"]), None) if history else None
    changes: dict[str, int] = {}
    if previous:
        for key, value in snapshot["counts"].items():
            old_value = previous["counts"].get(key, 0)
            if isinstance(value, (int, float)) and isinstance(old_value, (int, float)):
                changes[key] = value - old_value

    critical = [item for item in snapshot["alerts"] if item.get("severity") == "critical"]
    high = [item for item in snapshot["alerts"] if item.get("severity") == "high"]
    if critical:
        focus = "Сначала закройте просроченные или критичные пункты."
    elif high:
        focus = "В ближайшее время проверьте сроки и будущие списания."
    elif snapshot["counts"]["proposed_commitments"] or snapshot["counts"]["proposed_subscriptions"]:
        focus = "Проверьте новые предложения агента и подтвердите только корректные."
    else:
        focus = "Критичных изменений нет — можно сосредоточиться на запланированных делах."
    return {**snapshot, "history": history, "changes": changes,
            "state_of_me": {"focus": focus, "critical_count": len(critical),
                             "high_count": len(high),
                             "has_previous_snapshot": previous is not None}}
