# SQLite Backup & Restore Plan

## Current SQLite architecture
- DB path from `DATABASE_PATH` or default file near backend root: `backend/app/storage/db.py`
- Access pattern: per-operation connection context manager (`get_db_connection()`)
- Schema creation + lightweight in-place migration in `init_db()`
- Side tables include conversations, pending actions, memory, finance, countdowns, mail sync state
- No explicit WAL/journal mode configuration in current code

## Backup strategy (proposed)
- Use SQLite online backup API (`sqlite3.Connection.backup`) from a maintenance command.
- Backup format: `.sqlite3` file + metadata JSON (timestamp, app version, schema hash).
- Optional periodic schedule (daily + weekly) with retention policy.

## Frequency and retention
- Daily backup: keep 14 days
- Weekly backup: keep 8 weeks
- Monthly backup: keep 6 months

## Encryption and sensitive data
- DB contains potentially sensitive user content (emails previews, facts, conversations).
- At-rest encryption should be applied at storage layer (encrypted volume or encrypted archive).
- Secrets should remain in env files, not DB backups.

## Storage recommendations
- Primary local encrypted backup directory
- Optional off-device encrypted copy (user-controlled)

## Restore procedure (proposed)
1. Stop application process.
2. Copy current DB to emergency snapshot.
3. Replace DB file with selected backup.
4. Start application; allow `init_db()` to run non-destructive migration checks.
5. Validate critical API paths (`/health`, memory pending, finance summary, chat history read).

## Integrity verification
- Run `PRAGMA integrity_check;` after backup creation and after restore.
- Verify key table counts (conversations, user_facts, transactions).
- Log verification metadata.

## Disaster recovery notes
- Keep at least one offline backup.
- Document maximum acceptable data-loss window (RPO) and restore-time target (RTO).

## Proposed restore test scenario
1. Create backup.
2. Destroy a test DB copy.
3. Restore from backup.
4. Start application against restored DB.
5. Verify critical data paths and integrity checks pass.
