import json
import os
import sqlite3
import time
from pathlib import Path

import pytest


@pytest.fixture
def test_env(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_backup.db")
    backup_dir = str(tmp_path / "backups")

    monkeypatch.setattr(
        "backend.app.storage.backup.DB_PATH",
        db_path,
    )
    monkeypatch.setattr(
        "backend.app.storage.backup.BACKUP_DIR",
        backup_dir,
    )

    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY, content TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_facts (id INTEGER PRIMARY KEY, content TEXT)")
    conn.execute("INSERT INTO conversations (content) VALUES ('hello')")
    conn.execute("INSERT INTO user_facts (content) VALUES ('fact1')")
    conn.execute("INSERT INTO user_facts (content) VALUES ('fact2')")
    conn.commit()
    conn.close()

    return db_path, backup_dir


def test_create_backup_creates_file(test_env):
    db_path, backup_dir = test_env
    from backend.app.storage.backup import create_backup

    result = create_backup()

    assert result["status"] == "ok"
    assert result["integrity_check"] == "ok"
    assert result["table_counts"]["conversations"] == 1
    assert result["table_counts"]["user_facts"] == 2

    backup_path = result["backup_path"]
    assert os.path.exists(backup_path)
    assert os.path.exists(backup_path + ".json")

    with open(backup_path + ".json") as f:
        meta = json.load(f)
    assert meta["integrity_check"] == "ok"


def test_apply_retention_keeps_14(test_env):
    db_path, backup_dir = test_env
    from backend.app.storage.backup import apply_retention_policy

    os.makedirs(backup_dir, exist_ok=True)

    for i in range(20):
        ts = f"202608{i+1:02d}_120000" if i < 10 else f"202607{i+1:02d}_120000"
        stem = f"home_agent_{ts}"
        db_file = os.path.join(backup_dir, stem + ".sqlite3")
        json_file = os.path.join(backup_dir, stem + ".json")
        Path(db_file).touch()
        with open(json_file, "w") as f:
            json.dump({"timestamp": ts}, f)
        time.sleep(0.01)

    result = apply_retention_policy()

    assert result["kept"] == 14
    assert len(result["deleted"]) >= 10

    remaining = [f for f in os.listdir(backup_dir) if f.endswith(".sqlite3")]
    assert len(remaining) == 14

    for item in result["deleted"]:
        assert not os.path.exists(item)
        assert not os.path.exists(item.replace(".sqlite3", ".json"))


def test_restore_backup_from_clean_backup(test_env):
    db_path, backup_dir = test_env
    from backend.app.storage.backup import create_backup, restore_backup

    create_result = create_backup()
    backup_filename = os.path.basename(create_result["backup_path"])

    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS user_facts")
    conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()

    restore_result = restore_backup(backup_filename)

    assert restore_result["status"] == "ok"
    assert restore_result["integrity_check"] == "ok"
    assert os.path.exists(restore_result["pre_restore_snapshot"])

    conn = sqlite3.connect(db_path)
    row = conn.execute("PRAGMA integrity_check").fetchone()
    assert row[0] == "ok"
    count = conn.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0]
    assert count == 2
    conn.close()


def test_restore_backup_not_found(test_env):
    db_path, backup_dir = test_env
    from backend.app.storage.backup import restore_backup

    result = restore_backup("nonexistent.sqlite3")
    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_empty_backup_dir_retention(test_env):
    db_path, backup_dir = test_env
    from backend.app.storage.backup import apply_retention_policy

    os.makedirs(backup_dir, exist_ok=True)
    result = apply_retention_policy()
    assert result["kept"] == 0
    assert result["deleted"] == []
