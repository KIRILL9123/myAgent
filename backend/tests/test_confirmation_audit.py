from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlite3

from backend.app.agent.confirmation import cancel_callback, confirm_callback
from backend.app.storage import db


@pytest.fixture
def confirmation_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "confirmation-audit.db"))
    db.init_db()


def test_claim_enforces_channel_chat_and_session_identity(confirmation_db):
    action_id, nonce = db.save_pending_action(
        "telegram_123", "send_email", {"to": "owner@example.com"},
        source_channel="telegram", chat_id="123",
    )

    assert db.claim_pending_action(
        action_id, nonce, chat_id="999",
        source_channel="telegram", session_id="telegram_999",
    ) is None
    assert db.claim_pending_action(
        action_id, nonce, chat_id="123",
        source_channel="web", session_id="telegram_123",
    ) is None
    assert db.get_pending_action("telegram_123")["status"] == "pending"

    claimed = db.claim_pending_action(
        action_id, nonce, chat_id="123",
        source_channel="telegram", session_id="telegram_123",
    )
    assert claimed is not None
    assert db.claim_pending_action(
        action_id, nonce, chat_id="123",
        source_channel="telegram", session_id="telegram_123",
    ) is None


def test_sqlite_foreign_keys_are_enabled_on_each_connection(confirmation_db):
    with db.get_db_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO fact_relations "
                "(fact_a_id, fact_b_id, relation_type) VALUES (?, ?, ?)",
                (999_999, 999_998, "related"),
            )


@pytest.mark.asyncio
async def test_new_confirmation_has_bounded_expiry_and_expired_one_cannot_replay(confirmation_db):
    action_id, nonce = db.save_pending_action(
        "telegram_456", "send_email", {},
        source_channel="telegram", chat_id="456",
    )

    with db.get_db_connection() as conn:
        expires_at = conn.execute(
            "SELECT expires_at FROM pending_actions WHERE id = ?", (action_id,)
        ).fetchone()[0]
        assert expires_at is not None
        assert conn.execute(
            "SELECT expires_at > datetime('now') "
            "AND expires_at <= datetime('now', '+15 minutes') "
            "FROM pending_actions WHERE id = ?",
            (action_id,),
        ).fetchone()[0] == 1
        conn.execute(
            "UPDATE pending_actions SET expires_at = datetime('now', '-1 minute') "
            "WHERE id = ?",
            (action_id,),
        )
        conn.commit()

    assert db.get_pending_action("telegram_456") is None
    assert db.claim_pending_action(
        action_id, nonce, chat_id="456",
        source_channel="telegram", session_id="telegram_456",
    ) is None
    replay = await confirm_callback(nonce, "456", action_id=action_id)
    assert replay["code"] == "not_found"


def test_failure_reason_is_persisted_and_finalize_is_identity_bound(confirmation_db):
    action_id, nonce = db.save_pending_action(
        "telegram_123", "send_email", {},
        source_channel="telegram", chat_id="123",
    )
    assert db.claim_pending_action(
        action_id, nonce, chat_id="123",
        source_channel="telegram", session_id="telegram_123",
    ) is not None

    assert db.finalize_pending_action(
        action_id, "failed", "SMTP timeout",
        source_channel="telegram", chat_id="999", session_id="telegram_999",
    ) is False
    assert db.finalize_pending_action(
        action_id, "failed", "SMTP timeout",
        source_channel="telegram", chat_id="123", session_id="telegram_123",
    ) is True

    with db.get_db_connection() as conn:
        row = conn.execute(
            "SELECT status, failure_reason, resolved_at FROM pending_actions WHERE id = ?",
            (action_id,),
        ).fetchone()
    assert row[0] == "failed"
    assert row[1] == "SMTP timeout"
    assert row[2]


def test_only_one_concurrent_claim_succeeds(confirmation_db):
    action_id, nonce = db.save_pending_action(
        "web-session", "send_email", {}, source_channel="web",
    )

    def claim():
        return db.claim_pending_action(
            action_id, nonce, source_channel="web", session_id="web-session",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: claim(), range(2)))

    assert sum(result is not None for result in results) == 1


@pytest.mark.asyncio
async def test_telegram_callback_binds_action_id_and_chat(confirmation_db):
    action_id, nonce = db.save_pending_action(
        "telegram_123", "send_email", {},
        source_channel="telegram", chat_id="123",
    )

    wrong_chat = await confirm_callback(nonce, "999", action_id=action_id)
    assert wrong_chat["code"] == "not_found"

    wrong_action = await cancel_callback(nonce, "123", action_id=action_id + 1)
    assert wrong_action["code"] == "not_found"

    cancelled = await cancel_callback(nonce, "123", action_id=action_id)
    assert cancelled["status"] == "ok"

    replay = await cancel_callback(nonce, "123", action_id=action_id)
    assert replay["code"] == "not_found"
