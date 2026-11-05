"""Approval-gated links between active subscriptions and Finance templates.

The link creates a recurring template only after a second explicit approval. It
never creates a transaction immediately and it never deletes historical
transactions when a subscription is cancelled.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.storage.db import get_db_connection


LINK_STATUSES = {"PROPOSED", "LINKED", "DECLINED", "UNLINKED"}
MONTHLY_CYCLES = {"month", "monthly", "monthly billing", "ежемесячно", "ежемесячный"}
SUPPORTED_CURRENCIES = {"", "EUR", "€"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalized_cycle(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _subscription_linkability(subscription: dict[str, Any]) -> dict[str, Any]:
    if subscription.get("status") != "ACTIVE":
        return {"eligible": False, "reason": "Подписка ещё не активирована."}
    if subscription.get("amount") is None or float(subscription["amount"]) <= 0:
        return {"eligible": False, "reason": "Для финансового шаблона нужна положительная сумма."}
    if not subscription.get("next_charge_at"):
        return {"eligible": False, "reason": "Неизвестна дата следующего списания."}
    if _normalized_cycle(subscription.get("billing_cycle")) not in MONTHLY_CYCLES:
        return {"eligible": False, "reason": "Автоматически поддерживается только ежемесячный цикл."}
    currency = str(subscription.get("currency") or "").strip().upper()
    if currency not in SUPPORTED_CURRENCIES:
        return {"eligible": False, "reason": "Finance-шаблон пока поддерживает только EUR."}
    try:
        day = datetime.fromisoformat(str(subscription["next_charge_at"]).replace("Z", "+00:00")).day
    except (TypeError, ValueError) as exc:
        raise ValueError("next_charge_at must be a valid ISO-8601 datetime") from exc
    return {"eligible": True, "day_of_month": day, "currency": currency or "EUR"}


def get_subscription_finance_link(subscription_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT l.id, l.subscription_id, l.recurring_template_id, l.status,
                      l.approval_id, l.reason, l.created_at, l.updated_at,
                      l.linked_at, l.unlinked_at, t.active
               FROM subscription_finance_links l
               LEFT JOIN recurring_templates t ON t.id = l.recurring_template_id
               WHERE l.subscription_id = ?""",
            (subscription_id,),
        ).fetchone()
    if not row:
        return None
    keys = (
        "id", "subscription_id", "recurring_template_id", "status", "approval_id",
        "reason", "created_at", "updated_at", "linked_at", "unlinked_at",
        "template_active",
    )
    return dict(zip(keys, row))


def linked_recurring_template_ids() -> set[int]:
    """Return Finance templates already represented by active subscription signals."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT recurring_template_id
               FROM subscription_finance_links
               WHERE status = 'LINKED' AND recurring_template_id IS NOT NULL""",
        ).fetchall()
    return {int(row[0]) for row in rows}


def ensure_subscription_finance_proposal(
    subscription: dict[str, Any], source_channel: str = "web"
) -> dict[str, Any]:
    """Create or return the pending Finance-link approval for an active subscription."""
    linkability = _subscription_linkability(subscription)
    if not linkability["eligible"]:
        return {"status": "not_eligible", "reason": linkability["reason"]}

    link = get_subscription_finance_link(subscription["id"])
    if link and link["status"] == "LINKED":
        return {"status": "linked", **link}
    if link and link["status"] == "PROPOSED" and link.get("approval_id"):
        return {"status": "pending_approval", **link}

    now = _now()
    link_id = link["id"] if link else str(uuid.uuid4())
    with get_db_connection() as conn:
        if link:
            conn.execute(
                """UPDATE subscription_finance_links
                   SET status = 'PROPOSED', approval_id = NULL, reason = NULL,
                       updated_at = ?, unlinked_at = NULL
                   WHERE id = ?""",
                (now, link_id),
            )
        else:
            conn.execute(
                """INSERT INTO subscription_finance_links
                   (id, subscription_id, status, created_at, updated_at)
                   VALUES (?, ?, 'PROPOSED', ?, ?)""",
                (link_id, subscription["id"], now, now),
            )
        conn.commit()

    # Keep the approval store as the only user-facing proposal queue.
    from backend.app.approvals.approval_service import _upsert_request

    price = f"{float(subscription['amount']):g} {linkability['currency']}"
    day = linkability["day_of_month"]
    approval_id = _upsert_request(
        "SUBSCRIPTION_FINANCE_LINK",
        f"{link_id}:{uuid.uuid4().hex[:12]}",
        f"Добавить «{subscription['name']}» в Финансы",
        f"Создать ежемесячный шаблон {price} в категории «Подписки», начиная с {day}-го числа. Сами деньги не списываются автоматически.",
        {
            "link_id": link_id,
            "subscription_id": subscription["id"],
            "name": subscription["name"],
            "amount": subscription["amount"],
            "currency": linkability["currency"],
            "day_of_month": day,
            "source": "subscription_finance_link",
        },
        source_channel,
    )
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE subscription_finance_links SET approval_id = ?, updated_at = ? WHERE id = ?",
            (approval_id, _now(), link_id),
        )
        conn.commit()
    return {"status": "pending_approval", "id": link_id, "approval_id": approval_id}


def ensure_active_subscription_finance_proposals() -> None:
    from backend.app.subscriptions.subscription_service import list_subscriptions

    for subscription in list_subscriptions("ACTIVE"):
        existing = get_subscription_finance_link(subscription["id"])
        if existing and existing["status"] in {"DECLINED", "UNLINKED"}:
            # A rejection or an explicit unlink is a user decision. Do not
            # recreate noise on every Approval Center refresh; an explicit
            # re-approve/reopen path can call ensure_subscription_finance_proposal.
            continue
        ensure_subscription_finance_proposal(subscription)


def approve_subscription_finance_link(link_id: str, approval_id: str | None = None) -> dict[str, Any]:
    from backend.app.subscriptions.subscription_service import get_subscription

    with get_db_connection() as conn:
        link = conn.execute(
            "SELECT id, subscription_id, recurring_template_id, status FROM subscription_finance_links WHERE id = ?",
            (link_id,),
        ).fetchone()
    if not link:
        raise ValueError("financial link proposal not found")
    if link[3] == "LINKED":
        return get_subscription_finance_link(link[1]) or {}
    if link[3] != "PROPOSED":
        raise ValueError("financial link proposal is no longer pending")

    subscription = get_subscription(link[1])
    if not subscription:
        raise ValueError("subscription not found")
    linkability = _subscription_linkability(subscription)
    if not linkability["eligible"]:
        raise ValueError(linkability["reason"])

    now = _now()
    description = f"Подписка: {subscription['name']}"
    if subscription.get("provider"):
        description += f" ({subscription['provider']})"
    with get_db_connection() as conn:
        category = conn.execute("SELECT 1 FROM categories WHERE name = 'Подписки'").fetchone()
        if not category:
            raise ValueError("категория «Подписки» отсутствует в Finance")
        template_id = link[2]
        if template_id:
            existing = conn.execute("SELECT id FROM recurring_templates WHERE id = ?", (template_id,)).fetchone()
        else:
            existing = None
        if existing:
            conn.execute("UPDATE recurring_templates SET active = 1 WHERE id = ?", (template_id,))
        else:
            cursor = conn.execute(
                """INSERT INTO recurring_templates
                   (type, amount, currency, category, description, day_of_month, frequency, active)
                   VALUES ('expense', ?, ?, 'Подписки', ?, ?, 'monthly', 1)""",
                (float(subscription["amount"]), linkability["currency"], description, linkability["day_of_month"]),
            )
            template_id = cursor.lastrowid
        conn.execute(
            """UPDATE subscription_finance_links
               SET recurring_template_id = ?, status = 'LINKED', approval_id = COALESCE(?, approval_id),
                   reason = NULL, updated_at = ?, linked_at = COALESCE(linked_at, ?), unlinked_at = NULL
               WHERE id = ?""",
            (template_id, approval_id, now, now, link_id),
        )
        conn.commit()
    return get_subscription_finance_link(subscription["id"]) or {}


def decline_subscription_finance_link(link_id: str, reason: str | None = None) -> dict[str, Any]:
    link = get_subscription_finance_link_by_id(link_id)
    if not link:
        raise ValueError("financial link proposal not found")
    if link["status"] == "DECLINED":
        return link
    if link["status"] != "PROPOSED":
        raise ValueError("financial link proposal is no longer pending")
    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            """UPDATE subscription_finance_links
               SET status = 'DECLINED', reason = ?, updated_at = ?, approval_id = NULL
               WHERE id = ?""",
            (reason, now, link_id),
        )
        conn.commit()
    return get_subscription_finance_link_by_id(link_id) or {}


def get_subscription_finance_link_by_id(link_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT l.id, l.subscription_id, l.recurring_template_id, l.status,
                      l.approval_id, l.reason, l.created_at, l.updated_at,
                      l.linked_at, l.unlinked_at, t.active
               FROM subscription_finance_links l
               LEFT JOIN recurring_templates t ON t.id = l.recurring_template_id
               WHERE l.id = ?""",
            (link_id,),
        ).fetchone()
    if not row:
        return None
    return dict(zip(
        ("id", "subscription_id", "recurring_template_id", "status", "approval_id",
         "reason", "created_at", "updated_at", "linked_at", "unlinked_at", "template_active"),
        row,
    ))


def unlink_subscription_finance(subscription_id: str) -> dict[str, Any] | None:
    link = get_subscription_finance_link(subscription_id)
    if not link or link["status"] == "UNLINKED":
        return link
    now = _now()
    with get_db_connection() as conn:
        if link.get("recurring_template_id"):
            conn.execute(
                "UPDATE recurring_templates SET active = 0 WHERE id = ?",
                (link["recurring_template_id"],),
            )
        conn.execute(
            """UPDATE subscription_finance_links
               SET status = 'UNLINKED', approval_id = NULL, updated_at = ?, unlinked_at = ?
               WHERE id = ?""",
            (now, now, link["id"]),
        )
        conn.commit()
    return get_subscription_finance_link(subscription_id)
