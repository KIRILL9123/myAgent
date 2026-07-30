import sys
import unittest.mock as mock
import pytest


@pytest.fixture(autouse=True)
def _ensure_dry_run(monkeypatch):
    monkeypatch.delenv("EXECUTION_MODE", raising=False)


# ──────────────────────────────────────────────────────────────────────
# send_email
# ──────────────────────────────────────────────────────────────────────


def test_send_email_dry_run_returns_would_do():
    from backend.app.connectors.mail_connector import send_email

    result = send_email(to="test@test.com", subject="Subj", body="Body")

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "send_email"
    assert result["would_do"]["to"] == "test@test.com"
    assert result["would_do"]["subject"] == "Subj"
    assert result["would_do"]["account"] == "gmail"


def test_send_email_dry_run_does_not_call_smtp():
    from backend.app.connectors.mail_connector import send_email

    with mock.patch("smtplib.SMTP") as mock_smtp, mock.patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        result = send_email(to="test@test.com", subject="Subj", body="Body")

    assert result["status"] == "dry_run"
    mock_smtp.assert_not_called()
    mock_smtp_ssl.assert_not_called()


def test_send_email_with_account_dry_run():
    from backend.app.connectors.mail_connector import send_email

    result = send_email(to="test@test.com", subject="Subj", body="Body", account="ukrnet")

    assert result["status"] == "dry_run"
    assert result["would_do"]["account"] == "ukrnet"


def test_send_email_real_mode_calls_smtp(monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "real")

    from backend.app.connectors import mail_connector

    fake_config = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "user": "sender@example.com",
        "pwd": "test-password",
    }
    with mock.patch.object(mail_connector, "_get_account_config", return_value=fake_config), \
         mock.patch("smtplib.SMTP") as mock_smtp, mock.patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        instance = mock.MagicMock()
        mock_smtp.return_value = instance

        result = mail_connector.send_email(to="test@test.com", subject="Subj", body="Body")

    assert result["status"] == "success"
    mock_smtp.assert_called_once_with("smtp.example.com", 587)
    mock_smtp_ssl.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# create_event
# ──────────────────────────────────────────────────────────────────────


def test_create_event_dry_run_returns_would_do():
    from backend.app.connectors.caldav_connector import create_event

    result = create_event(title="Meeting", start_datetime="2026-08-01T10:00:00",
                          end_datetime="2026-08-01T11:00:00", description="Team sync")

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "create_event"
    assert result["would_do"]["title"] == "Meeting"
    assert result["would_do"]["start_datetime"] == "2026-08-01T10:00:00"
    assert result["would_do"]["end_datetime"] == "2026-08-01T11:00:00"
    assert result["would_do"]["description"] == "Team sync"


def test_create_event_dry_run_does_not_call_caldav():
    from backend.app.connectors.caldav_connector import create_event

    with mock.patch("caldav.DAVClient") as mock_dav:
        result = create_event(title="Test", start_datetime="2026-08-01T10:00:00")

    assert result["status"] == "dry_run"
    mock_dav.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# delete_event
# ──────────────────────────────────────────────────────────────────────


def test_delete_event_dry_run_returns_would_do():
    from backend.app.connectors.caldav_connector import delete_event

    result = delete_event(event_uid="my-event-uid")

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "delete_event"
    assert result["would_do"]["event_uid"] == "my-event-uid"


def test_delete_event_dry_run_does_not_call_caldav():
    from backend.app.connectors.caldav_connector import delete_event

    with mock.patch("caldav.DAVClient") as mock_dav:
        result = delete_event(event_uid="some-uid")

    assert result["status"] == "dry_run"
    mock_dav.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# modify_event
# ──────────────────────────────────────────────────────────────────────


def test_modify_event_dry_run_returns_would_do():
    from backend.app.connectors.caldav_connector import modify_event

    result = modify_event(event_uid="uid-1", updated_fields={"title": "New Title"})

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "modify_event"
    assert result["would_do"]["event_uid"] == "uid-1"
    assert result["would_do"]["updated_fields"] == {"title": "New Title"}


# ──────────────────────────────────────────────────────────────────────
# add_transaction
# ──────────────────────────────────────────────────────────────────────


def test_add_transaction_dry_run_returns_would_do():
    from backend.app.finance.finance_service import add_transaction

    result = add_transaction(type="expense", amount=500.0, category="Еда",
                             description="Обед", transaction_date="2026-08-01")

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "add_transaction"
    assert result["would_do"]["type"] == "expense"
    assert result["would_do"]["amount"] == 500.0
    assert result["would_do"]["category"] == "Еда"


def test_add_transaction_dry_run_does_not_write_to_db():
    from backend.app.finance.finance_service import add_transaction

    with mock.patch("backend.app.finance.finance_service.get_db_connection") as mock_conn:
        result = add_transaction(type="expense", amount=100.0, category="Еда",
                                 description="Test", transaction_date="2026-08-01")

    assert result["status"] == "dry_run"
    mock_conn.assert_not_called()


def test_add_transaction_dry_run_checks_type_validation():
    from backend.app.finance.finance_service import add_transaction

    result = add_transaction(type="invalid", amount=100.0, category="Еда",
                             description="Test", transaction_date="2026-08-01")

    assert result["status"] == "error"
    assert "type must be" in result["message"]


# ──────────────────────────────────────────────────────────────────────
# delete_transaction
# ──────────────────────────────────────────────────────────────────────


def test_delete_transaction_dry_run_returns_would_do():
    from backend.app.finance.finance_service import delete_transaction

    result = delete_transaction(transaction_id=42)

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "delete_transaction"
    assert result["would_do"]["transaction_id"] == 42


def test_delete_transaction_dry_run_does_not_write_to_db():
    from backend.app.finance.finance_service import delete_transaction

    with mock.patch("backend.app.finance.finance_service.get_db_connection") as mock_conn:
        result = delete_transaction(transaction_id=1)

    assert result["status"] == "dry_run"
    mock_conn.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# send_notification (Telegram)
# ──────────────────────────────────────────────────────────────────────


def test_send_notification_dry_run_returns_would_do():
    import asyncio
    from backend.app.notifications.telegram_notifier import send_notification

    result = asyncio.run(send_notification(message="Hello", chat_id="12345"))

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "send_notification"
    assert result["would_do"]["message"] == "Hello"
    assert result["would_do"]["chat_id"] == "12345"


def test_send_notification_real_mode_returns_bool(monkeypatch):
    import asyncio
    monkeypatch.setenv("EXECUTION_MODE", "real")

    from backend.app.notifications.telegram_notifier import send_notification

    with mock.patch("httpx.AsyncClient") as mock_client:
        instance = mock.AsyncMock()
        mock_rsp = mock.MagicMock()
        instance.post.return_value = mock_rsp
        mock_client.return_value.__aenter__.return_value = instance

        result = asyncio.run(send_notification(message="Hello"))

    assert isinstance(result, bool)
