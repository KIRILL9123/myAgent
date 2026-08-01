#!/usr/bin/env python3
"""
Interactive backup restore CLI.
WARNING: This replaces the active database. Requires EXECUTION_MODE=real.
"""
import os
import sys

# Safety: require explicit REAL mode
if os.getenv("EXECUTION_MODE", "dry_run").strip().lower() != "real":
    print("ERROR: This script requires EXECUTION_MODE=real. Aborting for safety.")
    print("Set EXECUTION_MODE=real in your .env file or environment, then re-run.")
    sys.exit(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.storage.backup import list_backups, restore_backup


def main():
    backups = list_backups()
    if not backups:
        print("No backups found.")
        return

    print(f"Found {len(backups)} backup(s):\n")
    for i, meta in enumerate(backups):
        ts = meta.get("timestamp", "unknown")
        tc = meta.get("table_counts", {})
        name = os.path.basename(meta.get("backup_path", "unknown"))
        print(f"  [{i}] {ts}  {name}")
        if tc:
            print(f"      conversations={tc.get('conversations', '?')}, "
                  f"user_facts={tc.get('user_facts', '?')}, "
                  f"transactions={tc.get('transactions', '?')}, "
                  f"countdowns={tc.get('countdowns', '?')}")

    try:
        choice = input("\nEnter backup number to restore (or Ctrl+C to abort): ").strip()
        idx = int(choice)
        if idx < 0 or idx >= len(backups):
            print(f"Invalid index: {idx}")
            return
    except (ValueError, KeyboardInterrupt):
        print("\nAborted.")
        return

    selected = backups[idx]
    backup_filename = os.path.basename(selected["backup_path"])

    print(f"\nWARNING: This will REPLACE the current database with backup:")
    print(f"  {selected['backup_path']}")
    print(f"  Timestamp: {selected.get('timestamp')}")
    print(f"  Table counts: {selected.get('table_counts')}")
    print()

    confirm = input("Type YES to confirm: ").strip()
    if confirm != "YES":
        print("Aborted.")
        return

    result = restore_backup(backup_filename)
    if result.get("status") == "ok":
        print(f"\nRestore successful.")
        print(f"  Integrity check: {result.get('integrity_check')}")
        print(f"  Pre-restore snapshot: {result.get('pre_restore_snapshot')}")
    else:
        print(f"\nRestore FAILED: {result.get('message')}")


if __name__ == "__main__":
    main()
