# Mira Workspace Rules & Context

## Operating Contract

- Treat the current repository, its tests, and its architecture documents as the source of truth. Inspect existing patterns before introducing new ones.
- Keep changes small, focused, reversible, and compatible with unrelated work already present in the working tree.
- Never expose, print, commit, or copy secrets from `.env`, local databases, logs, or integration credentials. Use `.env.example` for configuration documentation.
- Before claiming completion, run the smallest relevant validation and report any checks that could not be run.

## Code Map Integrity Gate

At the start of every code-changing task, compare the current repo with `docs/codemap/codemap.lock`.

Before modifying a module, use `docs/codemap/codemap.json` to answer three questions:

1. What calls it?
2. What does it affect?
3. Which tests cover it?

If the map is stale or cannot answer those questions, regenerate `codemap.html`, `codemap.json`, and `codemap.lock` before changing the code. Use the repository's reproducible codemap generator or documented tooling; do not silently rely on an outdated map.

Whenever module boundaries, dependencies, routes, databases, queues, or major data flows change, update the code map in the same commit as the code.

Treat the code map as generated project evidence: keep all generated outputs synchronized, review the diff for unexpected relationships, and do not hand-edit generated files unless the generator explicitly requires it.

## Product Architecture Gate

- Before product, UI, domain, API, or notification work, read `PRODUCT_ARCHITECTURE.md`, `DESIGN.md`, and `docs/templates/FEATURE_PROPOSAL.md`.
- Every new feature must have a completed proposal covering domain ownership, source of truth, UI placement, cross-domain behavior, Assistant/Telegram behavior, permissions, provenance, and non-goals.
- Do not add a new top-level route or domain until the proposal explains why an existing domain, page, tab, filter, detail view, or projection is insufficient.
- Keep Today, Personal State, and Action Center as projections; keep domain tables as the source of truth.
- When implementation changes ownership or placement, update the architecture and design documents in the same change.

## Implementation Rules

- Prefer existing utilities, services, schemas, and UI patterns over new abstractions or dependencies.
- For backend changes, preserve authentication, authorization, dry-run behavior, provenance, safety defaults, and async boundaries.
- For database changes, add a forward migration and keep already-applied migrations immutable.
- For API changes, consider existing clients, frontend queries, Telegram parity, error contracts, and backwards compatibility.
- For external integrations, avoid live side effects in tests and use explicit opt-in for real providers.
- For frontend changes, keep routing and data ownership aligned with the product architecture; avoid duplicating backend domain state in the UI.
- Every production-relevant bug fix must add or strengthen a regression test.
- Do not weaken, delete, or bypass a test merely to make a change pass. If behavior intentionally changes, update the contract and its tests together.

## Validation

- Backend tests: `python -m pytest backend/tests -q`
- Frontend checks: from `frontend`, run `npm run lint` and `npm run build`.
- Full deterministic release gate: `python dev-tools/release_gate.py`.
- Use live E2E or external integrations only when explicitly needed and configured; keep external side effects out of CI and sandbox runs.
- If a check fails, investigate the failure and either fix it or clearly report the remaining blocker. Do not claim success from an unverified change.

## Hardware Context & Constraints

- When developing on a fanless MacBook Air M4, keep current features lightweight. Avoid features that require continuous background generation, large RAG document chunking/embeddings, or real-time audio streaming (STT/TTS) during local development.
- Heavyweight features such as Whisper STT, Kokoro/Piper TTS, the Semantic Document Vault, and background IMAP email analysis should be implemented and profiled on the planned actively cooled Mac Mini M4 Pro setup.

## Active Priority Roadmap (MacBook Air Friendly)

1. Proactive Telegram alerts (fast APScheduler database scans + Telegram push).
2. Calendar conflict warning (zero-load frontend-only validation).
3. Chat budgeting consultant (fast read queries + one-shot short assistant answers).
