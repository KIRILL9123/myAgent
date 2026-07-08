# Decision Log & Notes

- **Date of Creation**: July 2, 2026
- **Calendar Provider**: We use **iCloud CalDAV** instead of Google Calendar. We connect using an `app-specific password`.
- **Mail Provider**: The mail provider is not yet finalized, but our working assumption for Phase 2 is **iCloud Mail** (via IMAP/SMTP on `imap.mail.me.com`).
- **Smart Home Integration**: This is a low priority. We plan to integrate with Home Assistant later (Phase 4-5) instead of designing IoT protocols from scratch.
- **Whitelist Permissions System**: Permissions are strictly enforced in Python code (`permission_checker.py`), NOT left to the LLM's discretion. This is a foundational security decision and must not be changed without explicit agreement.

---

## Phase 2 Technical Decisions (July 2, 2026)

- **CalDAV write operations**: Using `icalendar` library to build VCALENDAR/VEVENT payloads for `create_event`. The `caldav` library's `save_event()` accepts raw iCalendar strings. For `delete_event` and `modify_event`, we look up events by UID across all calendars.
- **Confirmation flow for RED actions**: Implemented using an in-memory dict (`_PENDING_ACTIONS`) keyed by `session_id`. No database needed at this stage. The user must reply with exact confirmation words ("да", "подтверждаю", etc.) to execute, or cancellation words to abort. The pending action is cleared after either outcome.
- **iCloud Mail via IMAP**: Uses `imaplib` (standard library) with `IMAP4_SSL` on port 993. We use `BODY.PEEK[]` to fetch emails without marking them as read. This preserves the mailbox state. Search is done via IMAP `SUBJECT` search criteria.
- **App-specific passwords**: iCloud CalDAV and iCloud Mail may use the **same** app-specific password, or separate ones depending on the user's preference. Both are configured independently in `.env` (`CALDAV_PASSWORD` vs `IMAP_PASSWORD`).
- **Language model behavior**: Added `CRITICAL LANGUAGE RULE` to the system prompt and lowered temperature to 0.3 to prevent `qwen2.5:7b` from mixing Russian with Chinese text.
- **System prompt datetime**: Changed from hardcoded date to `datetime.now()` so the agent always knows the current time.
- **delete_event / modify_event fallback**: The LLM often sends event titles instead of real CalDAV UIDs, especially with parallel tool calling (qwen2.5:7b calls `search_events` + `delete_event` in the same round before seeing search results). Solved by adding `_find_event_by_uid_or_title()` helper that tries UID lookup first, then falls back to title-based search across all calendars.
- **iCloud CalDAV caching**: After deleting events, `list_events` may still return them for a short period. This is likely iCloud-side propagation delay. Not a bug in our code — confirmed by audit log showing successful delete operations. Additionally, multiple test runs may create duplicate events with the same title.
- **Multi-turn tool calling loop**: Replaced single-round tool calling with a loop (max 5 iterations) so the LLM can chain calls (e.g., search → delete). Essential for complex operations.
- **Mail connector**: Originally built for iCloud, but corrected to support the user's real providers: **Gmail** and **ukr.net**. Uses `imaplib` (stdlib) with `BODY.PEEK[]` to avoid marking messages as read. The LLM selects the account via the `account` parameter (`"gmail"` or `"ukrnet"`). Credentials must be configured in `.env` (see `.env.example`).

## Phase 3 Completion
- **Scheduler**: Added `apscheduler` via FastAPI lifespan context manager.
- **Morning Summary**: The agent uses LLM to generate a summary of unread emails and today's events at `MORNING_SUMMARY_TIME`.
- **Telegram Notifications**: `telegram_notifier.py` handles proactive push notifications to the user using Telegram Bot API (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- **Email Sending**: Added SMTP sending to `mail_connector.py` for multiple providers (gmail, ukrnet). Added `send_email` to `tool_permissions.json` under `red` and implemented detailed confirmation in `orchestrator.py` showing To, Subject, and Body.
- **Reliability & Tool Cycle Limit (Priority 3)**: Implemented multiple safeguards to prevent infinite tool calling loops and hallucinations with Qwen2.5:
  1. **Early Stopping**: `orchestrator.py` tracks tool calls per round. If the agent repeats the exact same tool calls twice in a row, the loop breaks with a user-friendly error.
  2. **System Prompt Rules**: Added explicit instruction to NEVER retry the same tool call upon error, but explain it to the user.
  3. **Linear Tool Execution**: Disabled parallel tool calls (`parallel_tool_calls=False`) in `llm_client.py` payload to force linear reasoning.
  4. **JSON Retry Loop**: If the LLM generates invalid JSON for a tool call, the orchestrator returns the error back to the LLM (up to 2 times) to self-correct before giving up.

## Memory Layer (July 7, 2026)

- **Confirmation Flow for User Facts**: To ensure user data safety and prevent the agent from silently recording incorrect or irrelevant information, all newly extracted facts from conversations are saved with status `pending_approval`. They must be explicitly approved via API `/api/memory/{fact_id}/approve` before they can be utilized or linked.
- **Semantic Deduplication**: Before adding a fact as `pending_approval`, the agent checks for semantic similarity against existing approved and pending facts using the LLM. If a duplicate or minor variation is found, it updates the `updated_at` timestamp of the existing fact instead of creating a duplicate entry.
- **Relation Types Constraint**: To keep the knowledge graph clean, relation types between facts are restricted to a closed list: `related_to`, `contradicts`, `clarifies`, `causes`. The LLM is instructed to strictly select from this list when suggesting edges.
- **Automated Consolidation**: APScheduler runs `find_consolidation_candidates()` daily at 03:00. Results are cached in memory and served instantly when the user opens the Consolidation tab.
- **Extraction Guard**: The fact extraction prompt explicitly allows and encourages returning `[]` for fact-neutral queries (weather, time, tool requests) to prevent garbage pending facts.
- **Embedding Threshold**: `EMBEDDING_THRESHOLD = 100` in `memory_service.py`. When approved fact count exceeds this, a warning is logged recommending migration to embeddings-based retrieval.

### Known Limitation: N+1 LLM Calls in Memory Layer

Two operations exhibit an N+1 LLM call pattern (one LLM call per item in a loop):

1. **`backfill_isolated_relations()`** (`memory_service.py`):
   - For each isolated (unlinked) approved fact, makes a separate `suggest_relations()` call.
   - **Impact**: N isolated facts = N LLM calls. Each call passes ALL other approved facts as context.
   - **Estimate on qwen2.5:7b (local Ollama, ~3-5s per call)**:
     - 10 isolated facts → 30-50 seconds (acceptable)
     - 30 isolated facts → 90-150 seconds (noticeable, ~2 min)
     - 50+ isolated facts → 150-250+ seconds (>4 min, problematic)
   - **Potential fix**: Batch all isolated facts into a single LLM call that returns a relation matrix, but this increases prompt size significantly and may exceed context window.

2. **`extract_facts_from_conversation()`** (`fact_extractor.py`):
   - For each extracted raw fact, makes a separate deduplication LLM call against all existing facts.
   - **Impact**: M extracted facts per message = M dedup calls (typically 1-3 per message, so 3-15s extra latency).
   - **Estimate**: This runs in the background (fire-and-forget), so it doesn't block user responses. Only becomes a concern if extraction consistently yields 5+ facts per message, which is rare.
   - **Potential fix**: Send all candidates in a single batch dedup call.

3. **`approve_fact()` + `suggest_relations()`**: 1 LLM call per approval — this is intentional and correct (single-item operation).

4. **`find_consolidation_candidates()`**: 1 LLM call total (all facts in one prompt) — no N+1 issue.

**Conclusion**: At current scale (<30 approved facts), neither issue is noticeable. Backfill becomes the first bottleneck at ~50+ facts. Consider batching when the fact count approaches 50-100.

---

## Будущая фича: Языковой тренажёр (Ausbildung — English/German)

Контекст: пользователь начинает Ausbildung Mechatroniker в DHL с августа 2026, пишет конспекты на iPad, нужна помощь с английским и немецким языком, особенно техническая лексика.

Рассмотрены три подхода (не взаимоисключающие, можно комбинировать поэтапно):

1. **Словарный тренажёр (spaced repetition)** — новая SQLite таблица для карточек (термин на DE/EN/RU + история ответов), алгоритм интервальных повторений (Anki-подобный), Telegram присылает карточки на повторение по расписанию через APScheduler, пользователь отвечает текстом, агент проверяет и корректирует интервал. Технически самый простой вариант — чистая логика без OCR/мультимодальности.

2. **OCR-коррекция письменных работ** — пользователь фотографирует/экспортирует заметки с iPad (Notability/GoodNotes), отправляет в Telegram, агент делает OCR (нужен Tesseract или переход на мультимодальную модель вроде qwen2.5-vl вместо текстовой qwen2.5:7b) + грамматическая проверка через LLM с объяснением ошибок. Самый сложный вариант технически.

3. **Ежедневные генеративные упражнения** — встраивается в существующий morning_summary (APScheduler), агент генерирует короткое упражнение на немецком/английском (перевод, пропуск слова, мини-диалог технической тематики) каждое утро, пользователь отвечает, агент проверяет.

Рекомендованный порядок реализации при возврате к этой фиче: начать с варианта 1 (словарный тренажёр) как наименее сложного технически, затем вариант 3 (ежедневные упражнения используют ту же Telegram-инфраструктуру), вариант 2 (OCR) — в последнюю очередь, так как требует либо новую зависимость (Tesseract), либо смену модели на мультимодальную.

---

## Безопасность и Сессионная изоляция (8 июля 2026)

### 1. Авторизация по API-ключу (FastAPI + React)
- **Бэкенд**: Внедрено промежуточное ПО `api_key_auth_middleware` в [main.py](file:///Users/kyrylonaumov/Documents/coding/HomeAssistant/home-agent/backend/app/main.py). Оно перехватывает все запросы к маршрутам `/api/*` (за исключением `/api/health` и preflight OPTIONS-запросов CORS), проверяя заголовок `X-API-Key` на соответствие секрету `HOME_AGENT_API_KEY` из `.env`. В случае несовпадения возвращается код `401 Unauthorized`.
- **Фронтенд**: 
  - Настройки API-ключа вынесены в [frontend/.env](file:///Users/kyrylonaumov/Documents/coding/HomeAssistant/home-agent/frontend/.env) как `VITE_API_KEY`.
  - Запросы к API памяти в [memory.ts](file:///Users/kyrylonaumov/Documents/coding/HomeAssistant/home-agent/frontend/src/api/memory.ts) и чата в [chat.ts](file:///Users/kyrylonaumov/Documents/coding/HomeAssistant/home-agent/frontend/src/api/chat.ts) автоматически подмешивают этот заголовок во все HTTP-запросы через хелпер `getHeaders()`.

### 2. Сессионная изоляция чата (UUID v4)
- **Чат API**: Создан клиентский модуль [chat.ts](file:///Users/kyrylonaumov/Documents/coding/HomeAssistant/home-agent/frontend/src/api/chat.ts). Он содержит встроенный генератор UUID v4 `generateSessionId()`, использующий криптографически безопасный браузерный генератор `self.crypto.randomUUID()` с резервным псевдослучайным алгоритмом.
- **Изоляция**: Вместо общего статичного идентификатора `"default"` фронтенд будет генерировать уникальный in-memory UUID при инициализации сессии и передавать его в каждом POST-запросе к `/api/chat`. Это устраняет коллизии между открытыми вкладками и исключает ситуации, когда подтверждение опасных (RED) действий одного пользователя перехватывалось действиями другого.


