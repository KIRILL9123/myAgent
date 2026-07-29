import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.storage.db import DB_PATH

BACKUP_DIR = os.environ.get("BACKUP_DIR") or os.path.join(os.path.dirname(DB_PATH), "backups")


def create_backup() -> dict[str, Any]:
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"home_agent_{timestamp}.sqlite3"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    try:
        source = sqlite3.connect(DB_PATH)
        try:
            dest = sqlite3.connect(backup_path)
            try:
                source.backup(dest)
            finally:
                dest.close()
        finally:
            source.close()
    except Exception as e:
        return {"status": "error", "message": f"Backup failed: {e}"}

    integrity_result = _run_integrity_check(backup_path)

    table_counts = _count_tables(backup_path)

    meta = {
        "timestamp": timestamp,
        "source_path": DB_PATH,
        "backup_path": backup_path,
        "integrity_check": str(integrity_result) if integrity_result != "ok" else "ok",
        "table_counts": table_counts,
    }

    meta_path = backup_path + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {
        "status": "ok",
        "backup_path": backup_path,
        "integrity_check": str(integrity_result) if integrity_result == "ok" else integrity_result,
        "table_counts": table_counts,
    }


def list_backups() -> list[dict]:
    if not os.path.isdir(BACKUP_DIR):
        return []

    entries = []
    for fname in os.listdir(BACKUP_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(BACKUP_DIR, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    meta = json.load(f)
                    if "timestamp" in meta:
                        entries.append(meta)
            except (json.JSONDecodeError, KeyError):
                pass

    entries.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    return entries


def apply_retention_policy() -> dict[str, Any]:
    def _parse_timestamp(backup_name: str) -> datetime | None:
        stem = backup_name.removesuffix(".sqlite3").removesuffix(".json")
        ts_len = len("00000000_000000")
        if len(stem) < ts_len:
            return None
        ts_candidate = stem[-ts_len:]
        try:
            return datetime.strptime(ts_candidate, "%Y%m%d_%H%M%S")
        except ValueError:
            return None

    if not os.path.isdir(BACKUP_DIR):
        return {"deleted": [], "kept": 0}

    files = os.listdir(BACKUP_DIR)
    backup_stems = set()
    for f in files:
        if f.endswith(".sqlite3") and f.startswith("home_agent_"):
            stem = f.removesuffix(".sqlite3")
            backup_stems.add(stem)

    if not backup_stems:
        return {"deleted": [], "kept": 0}

    dated = [(stem, _parse_timestamp(stem + ".sqlite3")) for stem in backup_stems]
    dated = [(s, t) for s, t in dated if t is not None]
    dated.sort(key=lambda x: x[1], reverse=True)

    to_keep = 14
    deleted = []
    for stem, _ts in dated[to_keep:]:
        for ext in (".sqlite3", ".json"):
            path = os.path.join(BACKUP_DIR, stem + ext)
            if os.path.exists(path):
                os.remove(path)
                deleted.append(path)

    return {"deleted": deleted, "kept": min(len(dated), to_keep)}


def restore_backup(backup_filename: str) -> dict[str, Any]:
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.exists(backup_path):
        return {"status": "error", "message": f"Backup not found: {backup_filename}"}

    snapshot_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"pre_restore_snapshot_{snapshot_ts}.sqlite3"
    snapshot_path = os.path.join(BACKUP_DIR, snapshot_name)
    try:
        shutil.copy2(DB_PATH, snapshot_path)
    except Exception as e:
        return {"status": "error", "message": f"Failed to create pre-restore snapshot: {e}"}

    tmp_path = DB_PATH + ".restore_tmp"
    try:
        shutil.copy2(backup_path, tmp_path)
        os.replace(tmp_path, DB_PATH)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return {"status": "error", "message": f"Failed to restore backup: {e}"}

    integrity_result = _run_integrity_check(DB_PATH)

    return {
        "status": "ok",
        "restored_from": backup_path,
        "pre_restore_snapshot": snapshot_path,
        "integrity_check": str(integrity_result),
    }


# ─── helpers ──────────────────────────────────────────────────────────────────


def _run_integrity_check(db_path: str) -> str:
    try:
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            return row[0] if row else "no result"
        finally:
            conn.close()
    except Exception as e:
        return f"integrity check failed: {e}"


def _count_tables(db_path: str) -> dict[str, int]:
    tables = ("conversations", "user_facts", "transactions", "countdowns")
    counts = {}
    conn = sqlite3.connect(db_path)
    try:
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                counts[table] = row[0] if row else 0
            except sqlite3.OperationalError:
                counts[table] = 0
    finally:
        conn.close()
    return counts
