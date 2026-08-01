"""
Cycle 1 — Safety Boundary Hardening: Regression Tests.

Tests that every verified persistent-write path respects execution mode.
"""
import os
import sqlite3
import asyncio
import unittest.mock as mock
import pytest


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _ensure_dry_run(monkeypatch):
    """Default to dry_run for all tests — safe by construction."""
    monkeypatch.delenv("EXECUTION_MODE", raising=False)


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    """Create an isolated SQLite database for the test."""
    db_path = str(tmp_path / "test_safety.db")
    monkeypatch.setattr("backend.app.storage.db.DB_PATH", db_path)
    from backend.app.storage.db import init_db
    init_db()
    yield db_path


# ──────────────────────────────────────────────────────────────────────
# A. Countdown guards
# ──────────────────────────────────────────────────────────────────────


def test_add_countdown_dry_run_returns_would_do(test_db):
    from backend.app.countdown.countdown_service import add_countdown

    result = add_countdown("Test Deadline", "2026-12-31", "работа")

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "add_countdown"
    assert result["would_do"]["title"] == "Test Deadline"
    assert result["would_do"]["target_date"] == "2026-12-31"


def test_add_countdown_dry_run_does_not_write_to_db(test_db):
    from backend.app.countdown.countdown_service import add_countdown

    with mock.patch("backend.app.countdown.countdown_service.get_db_connection") as mock_conn:
        add_countdown("Test", "2026-12-31")
        mock_conn.assert_not_called()


def test_add_countdown_real_mode_writes_to_db(test_db, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "real")
    from backend.app.countdown.countdown_service import add_countdown
    from backend.app.storage.db import get_db_connection

    result = add_countdown("Real Deadline", "2026-12-31", "работа")

    assert result["status"] == "success"
    assert result["id"] is not None

    # Verify it's actually in the DB
    with get_db_connection() as conn:
        row = conn.execute("SELECT title, target_date FROM countdowns WHERE id = ?",
                           (result["id"],)).fetchone()
    assert row[0] == "Real Deadline"
    assert row[1] == "2026-12-31"


def test_delete_countdown_dry_run_returns_would_do(test_db):
    from backend.app.countdown.countdown_service import delete_countdown

    result = delete_countdown(42)

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "delete_countdown"
    assert result["would_do"]["countdown_id"] == 42


def test_delete_countdown_dry_run_does_not_mutate_db(test_db):
    from backend.app.countdown.countdown_service import delete_countdown

    with mock.patch("backend.app.countdown.countdown_service.get_db_connection") as mock_conn:
        delete_countdown(1)
        mock_conn.assert_not_called()


def test_delete_countdown_real_mode_deletes(test_db, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "real")
    from backend.app.countdown.countdown_service import add_countdown, delete_countdown
    from backend.app.storage.db import get_db_connection

    # Create a countdown first
    add_result = add_countdown("To Delete", "2026-12-31")
    cid = add_result["id"]

    # Delete it
    result = delete_countdown(cid)
    assert result["status"] == "success"

    # Verify gone
    with get_db_connection() as conn:
        row = conn.execute("SELECT id FROM countdowns WHERE id = ?", (cid,)).fetchone()
    assert row is None


# ──────────────────────────────────────────────────────────────────────
# B. Email sync-state guard
# ──────────────────────────────────────────────────────────────────────


def test_list_unread_emails_dry_run_does_not_update_sync_state(monkeypatch):
    """DRY_RUN mode must not permanently update last_seen_uid."""
    from backend.app.connectors.mail_connector import list_unread_emails, clear_mail_cache
    clear_mail_cache()  # avoid cache pollution between tests

    # Mock the IMAP connection
    with mock.patch("backend.app.connectors.mail_connector._connect") as mock_connect:
        mock_conn = mock.MagicMock()
        mock_conn.select.return_value = ("OK", None)
        mock_conn.search.return_value = ("OK", [b"1 2 3"])
        mock_conn.fetch.return_value = ("OK", [(b"1", b"From: test\r\nSubject: Test\r\n\r\nBody")])
        mock_connect.return_value = mock_conn

        # Mock the DB functions that list_unread_emails imports inline
        with mock.patch("backend.app.storage.db.get_last_seen_uid", return_value=0):
            with mock.patch("backend.app.storage.db.update_last_seen_uid") as mock_update:
                list_unread_emails(account="gmail", limit=5, bypass_last_seen=False)

    # update_last_seen_uid MUST NOT be called in dry_run
    mock_update.assert_not_called()


def test_list_unread_emails_real_mode_updates_sync_state(monkeypatch):
    """REAL mode should update last_seen_uid."""
    monkeypatch.setenv("EXECUTION_MODE", "real")
    from backend.app.connectors.mail_connector import list_unread_emails, clear_mail_cache
    clear_mail_cache()  # avoid cache pollution

    with mock.patch("backend.app.connectors.mail_connector._connect") as mock_connect:
        mock_conn = mock.MagicMock()
        mock_conn.select.return_value = ("OK", None)
        mock_conn.search.return_value = ("OK", [b"5 6 7"])
        mock_conn.fetch.return_value = ("OK", [(b"5", b"From: test\r\nSubject: Test\r\n\r\nBody")])
        mock_connect.return_value = mock_conn

        with mock.patch("backend.app.storage.db.get_last_seen_uid", return_value=0):
            with mock.patch("backend.app.storage.db.update_last_seen_uid") as mock_update:
                list_unread_emails(account="gmail", limit=5, bypass_last_seen=False)

    mock_update.assert_called_once()


# ──────────────────────────────────────────────────────────────────────
# C. Memory write guards
# ──────────────────────────────────────────────────────────────────────


def test_save_pending_fact_dry_run_returns_minus_one(test_db):
    from backend.app.memory.memory_service import save_pending_fact

    result = save_pending_fact("Test fact", "preference", 0.9)

    assert result == -1  # sentinel value for dry-run


def test_save_pending_fact_dry_run_does_not_write(test_db):
    from backend.app.memory.memory_service import save_pending_fact, get_pending_facts

    result = save_pending_fact("Should not persist", "habit", 0.8)

    assert result == -1
    pending = get_pending_facts()
    assert len(pending) == 0


def test_save_pending_fact_real_mode_writes(test_db, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "real")
    from backend.app.memory.memory_service import save_pending_fact, get_pending_facts

    fid = save_pending_fact("Real fact", "preference", 0.9)

    assert fid > 0
    pending = get_pending_facts()
    assert any(f["id"] == fid for f in pending)


def test_approve_fact_dry_run_no_db_write(test_db):
    from backend.app.memory.memory_service import save_pending_fact, approve_fact
    import asyncio

    # First create a fact in REAL mode so we have something to approve
    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        fid = save_pending_fact("Approve me", "habit", 0.8)

    # Now try approving in dry_run
    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=True):
        result = asyncio.run(approve_fact(fid))

    assert result is True  # Returns True (would succeed) but doesn't actually write
    # Verify status hasn't changed
    from backend.app.storage.db import get_db_connection
    with get_db_connection() as conn:
        row = conn.execute("SELECT status FROM user_facts WHERE id = ?", (fid,)).fetchone()
    assert row[0] == "pending_approval"


def test_approve_fact_real_mode_updates(test_db):
    from backend.app.memory.memory_service import save_pending_fact, approve_fact
    from backend.app.storage.db import get_db_connection
    import asyncio

    # Create fact in REAL mode
    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        fid = save_pending_fact("Really approve", "project", 0.7)

    # Approve in REAL mode — mock the inline import of suggest_relations
    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        with mock.patch("backend.app.memory.relation_builder.suggest_relations",
                        return_value=[]):
            result = asyncio.run(approve_fact(fid))

    assert result is True
    with get_db_connection() as conn:
        row = conn.execute("SELECT status FROM user_facts WHERE id = ?", (fid,)).fetchone()
    assert row[0] == "approved"


def test_reject_fact_dry_run_no_db_write(test_db):
    from backend.app.memory.memory_service import save_pending_fact, reject_fact

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        fid = save_pending_fact("Reject me", "other", 0.6)

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=True):
        result = reject_fact(fid)

    assert result is True
    from backend.app.storage.db import get_db_connection
    with get_db_connection() as conn:
        row = conn.execute("SELECT status FROM user_facts WHERE id = ?", (fid,)).fetchone()
    assert row[0] == "pending_approval"


def test_reject_fact_real_mode_updates(test_db):
    from backend.app.memory.memory_service import save_pending_fact, reject_fact
    from backend.app.storage.db import get_db_connection

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        fid = save_pending_fact("Really reject", "other", 0.5)

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        result = reject_fact(fid)

    assert result is True
    with get_db_connection() as conn:
        row = conn.execute("SELECT status FROM user_facts WHERE id = ?", (fid,)).fetchone()
    assert row[0] == "rejected"


def test_consolidate_facts_dry_run_no_write(test_db):
    from backend.app.memory.memory_service import consolidate_facts

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=True):
        result = consolidate_facts([1, 2], "Merged content", "preference")

    assert result == -1  # sentinel for dry-run


def test_consolidate_facts_real_mode(test_db):
    from backend.app.memory.memory_service import (
        save_pending_fact, approve_fact, consolidate_facts
    )
    from backend.app.storage.db import get_db_connection
    import asyncio

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        f1 = save_pending_fact("Fact A", "preference", 0.9)
        f2 = save_pending_fact("Fact B similar to A", "preference", 0.9)
        # Approve both
        with mock.patch("backend.app.memory.relation_builder.suggest_relations", return_value=[]):
            asyncio.run(approve_fact(f1))
            asyncio.run(approve_fact(f2))

        new_id = consolidate_facts([f1, f2], "Consolidated fact", "preference")

    assert new_id > 0
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT content, status FROM user_facts WHERE id = ?", (new_id,)
        ).fetchone()
    assert row[0] == "Consolidated fact"
    assert row[1] == "approved"


def test_save_relation_dry_run_no_write(test_db):
    from backend.app.memory.memory_service import save_relation

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=True):
        result = save_relation(1, 2, "related_to")

    assert result is True  # would succeed
    # Verify not in DB
    from backend.app.storage.db import get_db_connection
    with get_db_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM fact_relations").fetchone()[0]
    assert count == 0


def test_update_fact_timestamp_dry_run_no_write(test_db):
    from backend.app.memory.memory_service import save_pending_fact, update_fact_timestamp
    from backend.app.storage.db import get_db_connection

    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=False):
        fid = save_pending_fact("Timestamp test", "habit", 0.8)

    # Record the current timestamp
    with get_db_connection() as conn:
        before = conn.execute(
            "SELECT updated_at FROM user_facts WHERE id = ?", (fid,)
        ).fetchone()[0]

    # Try updating in dry_run
    with mock.patch("backend.app.memory.memory_service.is_dry_run", return_value=True):
        update_fact_timestamp(fid)

    # Verify timestamp has NOT changed
    with get_db_connection() as conn:
        after = conn.execute(
            "SELECT updated_at FROM user_facts WHERE id = ?", (fid,)
        ).fetchone()[0]
    assert after == before


# ──────────────────────────────────────────────────────────────────────
# D. Telegram guard
# ──────────────────────────────────────────────────────────────────────


def test_send_notification_dry_run_returns_would_do():
    from backend.app.notifications.telegram_notifier import send_notification

    result = asyncio.run(send_notification(message="Test", chat_id="12345"))

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "send_notification"


def test_send_notification_dry_run_no_http_call():
    from backend.app.notifications.telegram_notifier import send_notification

    with mock.patch("httpx.AsyncClient") as mock_client:
        asyncio.run(send_notification(message="Test"))
        mock_client.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# E. Recurring template guards
# ──────────────────────────────────────────────────────────────────────


def test_add_recurring_template_dry_run_returns_would_do(test_db):
    from backend.app.finance.finance_service import add_recurring_template

    result = add_recurring_template("expense", 500.0, "Еда", "Monthly food", 15)

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "add_recurring_template"
    assert result["would_do"]["amount"] == 500.0


def test_delete_recurring_template_dry_run_returns_would_do(test_db):
    from backend.app.finance.finance_service import delete_recurring_template

    result = delete_recurring_template(42)

    assert result["status"] == "dry_run"
    assert result["would_do"]["action"] == "delete_recurring_template"


def test_process_recurring_transactions_dry_run_no_inserts(test_db, monkeypatch):
    """DRY_RUN mode: process_recurring_transactions must not insert transactions."""
    # Ensure dry_run via env
    monkeypatch.setenv("EXECUTION_MODE", "dry_run")
    from backend.app.finance.finance_service import (
        add_recurring_template, process_recurring_transactions
    )
    from backend.app.storage.db import get_db_connection

    # Create a template that would trigger today (in REAL mode)
    import datetime
    today = datetime.date.today()
    monkeypatch.setenv("EXECUTION_MODE", "real")
    add_recurring_template("expense", 100.0, "Еда", "Daily trigger", today.day)

    # Count transactions before
    with get_db_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    # Run in dry_run mode
    monkeypatch.setenv("EXECUTION_MODE", "dry_run")
    process_recurring_transactions()

    # Verify no new transactions were created
    with get_db_connection() as conn:
        after = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert after == before


# ──────────────────────────────────────────────────────────────────────
# F. API endpoint safety (via service guards)
# ──────────────────────────────────────────────────────────────────────


def test_api_add_countdown_respects_dry_run(test_db):
    """API route calls service directly; service guard protects it."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    os.environ["HOME_AGENT_API_KEY"] = "test-key"
    client = TestClient(app)
    headers = {"X-API-Key": "test-key"}

    resp = client.post(
        "/api/countdown/",
        json={"title": "Test API", "target_date": "2026-12-31", "category": "работа"},
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dry_run"
    assert data["would_do"]["title"] == "Test API"


def test_api_delete_countdown_respects_dry_run(test_db):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    os.environ["HOME_AGENT_API_KEY"] = "test-key"
    client = TestClient(app)
    headers = {"X-API-Key": "test-key"}

    resp = client.delete("/api/countdown/999", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dry_run"


# ──────────────────────────────────────────────────────────────────────
# G. Permission policy review: delete_countdown is YELLOW by design
# ──────────────────────────────────────────────────────────────────────


def test_delete_countdown_permission_is_yellow():
    """Verify delete_countdown remains YELLOW (documented design decision)."""
    from backend.app.permissions.permission_checker import check_permission, PermissionLevel

    level = check_permission("delete_countdown")
    assert level == PermissionLevel.YELLOW


def test_delete_event_permission_is_red():
    """Verify delete_event is RED (external system mutation)."""
    from backend.app.permissions.permission_checker import check_permission, PermissionLevel

    level = check_permission("delete_event")
    assert level == PermissionLevel.RED
