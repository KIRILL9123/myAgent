from datetime import datetime, timezone

import pytest

from backend.app.approvals.approval_service import list_approvals, resolve_approval
from backend.app.finance.finance_service import get_recurring_templates
from backend.app.storage import db
from backend.app.subscriptions.subscription_service import create_subscription, transition_subscription


@pytest.fixture
def link_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "subscription-finance.db"))
    db.init_db()


@pytest.mark.asyncio
async def test_subscription_finance_link_requires_second_approval_and_is_idempotent(link_db):
    subscription = create_subscription(
        "Streaming Pro",
        provider="Streaming",
        subscription_type="PAID",
        amount=12.99,
        currency="EUR",
        billing_cycle="monthly",
        next_charge_at="2030-01-10T12:00:00+00:00",
    )

    subscription_approval = list_approvals()[0]
    await resolve_approval(subscription_approval["id"], "approve")

    pending = list_approvals()
    assert len(pending) == 1
    assert pending[0]["kind"] == "SUBSCRIPTION_FINANCE_LINK"
    assert "ежемесячный шаблон" in pending[0]["summary"]

    linked = await resolve_approval(pending[0]["id"], "approve")
    assert linked["status"] == "APPROVED"

    templates = get_recurring_templates()
    assert len(templates) == 1
    assert templates[0]["active"] is True
    assert templates[0]["day_of_month"] == 10

    # Reconciliation must not create a second link or template.
    assert list_approvals() == []
    assert len(get_recurring_templates()) == 1


@pytest.mark.asyncio
async def test_linked_subscription_template_is_not_duplicated_in_action_center(link_db):
    subscription = create_subscription(
        "Streaming Pro",
        amount=12.99,
        currency="EUR",
        billing_cycle="monthly",
        next_charge_at="2030-01-10T12:00:00+00:00",
    )
    transition_subscription(subscription["id"], "approve")
    from backend.app.finance.subscription_link_service import ensure_subscription_finance_proposal

    proposal = ensure_subscription_finance_proposal({**subscription, "status": "ACTIVE"})
    await resolve_approval(proposal["approval_id"], "approve")

    from backend.app.action_center_service import build_action_center

    result = build_action_center(
        datetime(2030, 1, 8, 12, tzinfo=timezone.utc),
        include_external=False,
    )

    assert any(item["kind"] == "subscription" for item in result["actions"])
    assert not any(item["kind"] == "finance" for item in result["actions"])


@pytest.mark.asyncio
async def test_cancelling_subscription_stops_future_finance_projection(link_db):
    subscription = create_subscription(
        "Monthly Tool",
        amount=5,
        currency="EUR",
        billing_cycle="monthly",
        next_charge_at="2030-02-15T12:00:00+00:00",
    )
    transition_subscription(subscription["id"], "approve")
    from backend.app.finance.subscription_link_service import ensure_subscription_finance_proposal

    proposal = ensure_subscription_finance_proposal({**subscription, "status": "ACTIVE"})
    await resolve_approval(proposal["approval_id"], "approve")

    cancelled = transition_subscription(subscription["id"], "cancel")
    assert cancelled["status"] == "CANCELLED"
    assert get_recurring_templates()[0]["active"] is False


@pytest.mark.asyncio
async def test_unknown_cycle_does_not_create_finance_proposal(link_db):
    subscription = create_subscription(
        "Annual Tool",
        amount=60,
        currency="EUR",
        billing_cycle="yearly",
        next_charge_at="2030-03-01T12:00:00+00:00",
    )
    transition_subscription(subscription["id"], "approve")
    from backend.app.finance.subscription_link_service import ensure_subscription_finance_proposal

    result = ensure_subscription_finance_proposal({**subscription, "status": "ACTIVE"})
    assert result["status"] == "not_eligible"
    assert "ежемесячный" in result["reason"]
    assert get_recurring_templates() == []


@pytest.mark.asyncio
async def test_declined_finance_link_does_not_reappear_on_refresh(link_db):
    subscription = create_subscription(
        "Declined Tool",
        amount=8,
        currency="EUR",
        billing_cycle="monthly",
        next_charge_at="2030-04-01T12:00:00+00:00",
    )
    transition_subscription(subscription["id"], "approve")
    from backend.app.finance.subscription_link_service import ensure_subscription_finance_proposal

    proposal = ensure_subscription_finance_proposal({**subscription, "status": "ACTIVE"})
    await resolve_approval(proposal["approval_id"], "reject")
    assert list_approvals() == []
