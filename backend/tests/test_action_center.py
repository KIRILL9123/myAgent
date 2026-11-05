from datetime import datetime, timezone

import pytest

from backend.app.storage import db


@pytest.fixture
def action_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "actions.db"))
    db.init_db()


def test_action_center_normalizes_attention_and_approval(action_db):
    from backend.app.action_center_service import build_action_center
    from backend.app.commitments.commitment_service import create_commitment, transition_commitment
    from backend.app.subscriptions.subscription_service import create_subscription, transition_subscription

    overdue_commitment = create_commitment(
        "Отправить отчёт",
        source_type="CHAT",
        deadline_at="2030-01-01T10:00:00+00:00",
    )
    transition_commitment(overdue_commitment["id"], "approve")
    subscription = create_subscription(
        "Video trial",
        subscription_type="TRIAL",
        amount=9.99,
        currency="EUR",
        trial_ends_at="2030-01-12T10:00:00+00:00",
        reminder_at="2030-01-10T10:00:00+00:00",
        source_type="EMAIL",
    )
    transition_subscription(subscription["id"], "approve")
    create_commitment("Проверить предложенную задачу", source_type="EMAIL")

    result = build_action_center(
        datetime(2030, 1, 10, 12, tzinfo=timezone.utc),
        include_external=False,
    )
    actions = result["actions"]

    assert result["summary"]["total"] == 3
    assert result["summary"]["overdue"] == 1
    assert result["summary"]["requires_approval"] == 1
    assert actions[0]["kind"] == "commitment"
    assert actions[0]["priority"] == "critical"
    subscription_action = next(item for item in actions if item["kind"] == "subscription")
    assert subscription_action["reminder_due"] is True
    assert subscription_action["metadata"]["currency"] == "EUR"
    approval_action = next(item for item in actions if item["kind"] == "approval")
    assert approval_action["status"] == "needs_approval"
    assert approval_action["target"] == "/approvals"


def test_action_center_all_mode_includes_planned_items(action_db):
    from backend.app.action_center_service import build_action_center
    from backend.app.commitments.commitment_service import create_commitment, transition_commitment

    commitment = create_commitment(
        "Запланированное дело",
        source_type="CHAT",
        deadline_at="2030-03-01T10:00:00+00:00",
    )
    transition_commitment(commitment["id"], "approve")
    reference_time = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)

    attention = build_action_center(reference_time, mode="attention", include_external=False)
    all_actions = build_action_center(reference_time, mode="all", include_external=False)

    assert attention["actions"] == []
    assert any(item["source_id"] == commitment["id"] for item in all_actions["actions"])


def test_action_center_projects_next_finance_occurrence(action_db, real_mode):
    from backend.app.action_center_service import build_action_center
    from backend.app.finance.finance_service import add_recurring_template

    add_recurring_template(
        "expense",
        19.99,
        "Подписки",
        "Music plan",
        currency="EUR",
        frequency="monthly",
        day_of_month=12,
    )

    result = build_action_center(
        datetime(2030, 1, 10, 12, tzinfo=timezone.utc),
        include_external=False,
    )
    action = next(item for item in result["actions"] if item["kind"] == "finance")

    assert action["title"] == "Расход: Music plan"
    assert action["status"] == "upcoming"
    assert action["priority"] == "high"
    assert action["reminder_due"] is False
    assert action["due_at"] == "2030-01-12"
    assert action["target"] == "/finance"
    assert action["metadata"]["currency"] == "EUR"

    due_today = build_action_center(
        datetime(2030, 1, 12, 12, tzinfo=timezone.utc),
        include_external=False,
    )
    assert next(item for item in due_today["actions"] if item["kind"] == "finance")["reminder_due"] is True


def test_action_center_includes_open_error_reports(action_db):
    from backend.app.action_center_service import build_action_center
    from backend.app.observability.error_reports import create_error_report, update_error_report

    report = create_error_report("Calendar timeout", "Calendar did not respond.", severity="high", correlation_id="corr-error")
    result = build_action_center(include_external=False)
    error_action = next(item for item in result["actions"] if item["kind"] == "error")
    assert error_action["source_id"] == str(report["id"])
    assert error_action["target"] == "/errors"
    assert error_action["priority"] == "high"

    update_error_report(report["id"], "fixing")
    all_actions = build_action_center(mode="all", include_external=False)
    assert any(item["id"] == f"error:{report['id']}" for item in all_actions["actions"])


def test_action_center_interaction_state_filters_attention(action_db):
    from backend.app.action_center_service import build_action_center
    from backend.app.action_state_service import set_action_state
    from backend.app.commitments.commitment_service import create_commitment, transition_commitment

    commitment = create_commitment(
        "Проверить Action Center",
        source_type="CHAT",
        deadline_at="2030-01-10T10:00:00+00:00",
    )
    transition_commitment(commitment["id"], "approve")
    reference_time = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)

    first = build_action_center(reference_time, include_external=False)
    assert first["actions"][0]["interaction"]["state"] == "unread"

    set_action_state(f"commitment:{commitment['id']}", "read")
    assert build_action_center(reference_time, include_external=False)["actions"] == []
    all_actions = build_action_center(reference_time, mode="all", include_external=False)
    assert all_actions["actions"][0]["interaction"]["state"] == "read"
    assert all_actions["summary"]["read"] == 1

    set_action_state(
        f"commitment:{commitment['id']}",
        "snoozed",
        snoozed_until="2030-01-11T10:00:00+00:00",
    )
    assert build_action_center(reference_time, include_external=False)["actions"] == []
    resumed = build_action_center(datetime(2030, 1, 12, tzinfo=timezone.utc), include_external=False)
    assert resumed["actions"][0]["interaction"]["state"] == "unread"

    set_action_state(f"commitment:{commitment['id']}", "dismissed")
    assert build_action_center(datetime(2030, 1, 12, tzinfo=timezone.utc), include_external=False)["actions"] == []
