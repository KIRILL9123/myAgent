# Roadmap

## Phase 1: Foundation (Completed)
- [x] Project scaffolding and documentation
- [x] FastAPI entrypoint
- [x] Whitelist permission system (green/yellow/red)
- [x] Tool calling loop with Ollama (local LLM)
- [x] iCloud CalDAV connector (Read-only: list/search events)

## Phase 2: Calendar Management & Email Reader
**Status: COMPLETED**
- [x] Create CalDAV connector with write capabilities
- [x] Implement multi-turn confirmation loop for safety
- [x] Create Email connector (IMAP) for reading emails
- [x] Update tool_permissions.json with new actions
- [x] Update frontend UI for basic chat capabilities

### Phase 3: Proactive Background Tasks 
**Status: COMPLETED**
- **Scheduler**: Added `apscheduler` and running as a background task.
- **Morning Summary Task**: Agent checks email/calendar every morning and generates an LLM summary.
- **Email Sending**: Agent can send emails via SMTP (requires explicit RED permission confirmation).
- **Notifications**: Summary is sent directly to the user via Telegram Bot API.

## Phase 4: Finance Module (MVP)
**Status: COMPLETED**
- [x] Create database tables for transactions and categories
- [x] Implement backend finance service and API endpoints
- [x] Register finance tools for the agent (green permission)
- [x] Refactor frontend into a multi-module dashboard (Chat, Finance)

## Phase 4.5: Countdowns / Deadlines
**Status: COMPLETED**
- [x] Create database table `countdowns`
- [x] Implement `countdown_service.py`
- [x] Add tools `add_countdown`, `get_all_countdowns`, `delete_countdown`
- [x] Add frontend Deadlines tab
- [x] Include countdowns in morning summary

## Phase 5: Voice Telegram Integration
**Status: COMPLETED**
- [x] Add `openai-whisper` for local voice recognition
- [x] Implement audio transcription in `backend/app/voice/transcriber.py`
- [x] Update Telegram listener to download and transcribe voice messages

## Phase 6: Smart Home Integration
**Status: POSTPONED (отложена по решению пользователя, не приоритет)**
- [ ] Connect to Home Assistant (REST/WebSocket API)
- [ ] Read-only state access for sensors and lights

## Phase 7: Complete Home Automation
- [ ] Allow the agent to control Home Assistant devices (turn on lights, adjust thermostat)
- [ ] Refine remote access via Tailscale and secure the web interface

## Phase 8: Memory Layer (Stable ✅ — future optimizations documented in NOTES.md)
- [x] Create SQLite DB schema for user facts and relations
- [x] Implement LLM fact extractor with semantic deduplication check
- [x] Implement LLM relation builder with closed type list
- [x] Create confirmation flow REST endpoints (get pending, approve, reject, get graph data)
- [x] Scaffold React + Vite + TS + Tailwind CSS frontend
- [x] Build Obsidian-style interactive force-directed memory graph view (visual styling, search query highlights, camera zoom controls, and slide-out details panel)
- [x] Add Approve/Reject pending facts review queue UI
- [x] Add backend relations backfill endpoint and trigger button in UI
- [x] Implement semantic fact consolidation flow (clustering candidates, POST-merge status update, and UI tab)

## Phase 8.1: Memory Integration in Orchestrator (Stable ✅)
- [x] Implement LLM-based `get_relevant_facts()` retrieval in `memory_service.py`
- [x] Inject relevant approved facts into orchestrator system prompt
- [x] Add background `extract_facts_from_conversation()` call after each LLM response
- [x] Replace Mem0/Qdrant integration with custom Memory Layer (human-in-the-loop)
- [x] Add debug logging for retrieved facts (`[MEMORY]` prefix in server logs)
- [x] Automated nightly consolidation via APScheduler (03:00, results cached for instant tab load)
- [x] Extraction guard: prompt explicitly allows `[]` for fact-neutral queries
- [x] Embedding threshold warning at >100 facts (`EMBEDDING_THRESHOLD` constant)
- [x] N+1 LLM call audit documented in NOTES.md (backfill + dedup patterns)
- [ ] При росте базы фактов (>100) рассмотреть переход на embeddings-based retrieval вместо LLM-фильтрации всего списка
- [ ] При росте до 50+ фактов рассмотреть batch-версию backfill_isolated_relations и dedup

## Phase 8.2: Security & Session Isolation (Stable ✅)
- [x] Session isolation: unique UUID v4 generated in-memory per frontend tab to prevent confirmation race conditions
- [x] API Key Authorization: FastAPI middleware validating `X-API-Key` on `/api/*` routes (with preflight OPTIONS and health check bypass)
- [x] Prompt Injection Guard: automatic XML wrapping of untrusted external content (emails and calendar)
- [x] Network Bind: host `0.0.0.0` architectural decision documented and protected via API-Key auth
- [x] Mobile responsive layout fix: memory legend and node details converted into elegant bottom sheets on mobile devices (<640px)

## Phase 9: Unified Dashboard & Chat UI (Stable ✅)
- [x] Dashboard Navigation Shell: AppShell layout component with a left vertical sidebar on desktop and bottom navigation tabs on mobile, routing `/` to `/dashboard`
- [x] Dashboard Home Screen: responsive grid of clickable widgets (Calendar today, Finance monthly net, Urgent countdowns, Unread emails) with skeleton loaders and isolated error handling
- [x] Chat UI: full-featured interactive chat interface supporting session isolation, loading states, and inline confirmation controls
- [x] Calendar Page: direct calendar event management and CRUD endpoints (Today/Week/Month views, modals, edit/delete actions, background CalDAV threads)
- [x] Mail Page: unread listing, search, and direct compose/reply SMTP flow with double-step preview (Gmail/UkrNet selector, search field, reply pre-fill, preview modal)
- [x] Finance Page: direct transaction logging and summaries module with Category Expense Bar Chart (recharts), monthly Active Subscriptions list, and Repeat monthly toggle
- [x] Countdowns Page: direct countdowns/timer logs list with urgent highlights (days remaining calculation, urgent styling < 30 days, category tags, delete deadlines)

## Phase 9.1: Long-Running Resource Audit & Optimization (Stable ✅)
- [x] SQLite Connection Leak Fix: wrap all database operations in `get_db_connection()` context manager to guarantee connection closing on errors
- [x] Ollama Connection Pooling: reuse a single persistent global `httpx.AsyncClient` across all model queries with lifespan cleanup
- [x] Log Rotation: configure `RotatingFileHandler` with 5MB maxBytes and 3 backups rotation for `audit.log` and `summaries.log`

## Open Technical Debt (Backlog)
- [ ] DRY refactoring: consolidate fetch, loading state, and error handling in frontend components (graph, review, consolidation) into a reusable hook/service
- [ ] Accessibility (A11y) improvements: add standard ARIA labels, tab index controls, and keyboard navigation support to frontend components

## Backlog / Future Ideas
- [ ] Языковой тренажёр для Ausbildung (English/German) — детали в NOTES.md, три подхода рассмотрены, старт с варианта 1 (spaced repetition словарь)

## Backlog: Product Ideas
- [ ] Логика агента: проактивное предложение транзакций — если в письме обнаружен чек/квитанция о покупке, агент должен предлагать пользователю "хочешь я запишу это как расход в Finance?" вместо ожидания ручного ввода. Требует доработки orchestrator.py и, возможно, отдельного анализа содержимого писем на предмет финансовых документов.
- [ ] Финансы: проактивные алерты в Telegram — бот отслеживает темп трат по категориям и предупреждает при превышении лимитов (например: «Кирилл, на этой неделе расходы на категорию "Еда" выросли на 30% выше твоего обычного лимита. Притормозим?»).
- [ ] Дедлайны: умные проактивные напоминания в Telegram — бот напоминает о дедлайнах интерактивным языком вместо сухих цифр (например: «До сдачи проекта Ausbildung осталось 3 дня. Ты просил напомнить. Всё готово или нужно перенести встречу?»).
- [ ] Голосовое управление: локальный Speech-to-Text (STT) — кнопка микрофона в веб-чате, использующая whisper.cpp локально на Mac для расшифровки голоса.
- [ ] Голосовое управление: локальный Text-to-Speech (TTS) — интеграция Kokoro / Piper TTS для озвучивания ответов бота (например, подтверждение добавления транзакции голосом).
- [ ] Почта: авто-события из писем — агент в фоне парсит подтверждения бронирования (отели, авиабилеты, запись к врачу) и предлагает внести их в календарь.
- [ ] Чат: контекстные подсказки на основе бюджета — агент отвечает на вопросы о покупках (например: «Могу я купить этот монитор за 30 000 руб?») анализируя реальный баланс в Finance.
- [ ] Интерфейс: интерактивные виджеты дашборда — поддержка Drag-and-Drop и изменения размеров виджетов на главной странице (Gridstack).
- [ ] Интерфейс: тёмная тема нового поколения — матовое стекло (Glassmorphism), View Transitions API для плавной анимации страниц, интерактивные hover-эффекты на графиках.
- [ ] Calendar: детектор конфликтов — при создании/изменении события в CalendarPage.tsx, если новое время пересекается с уже существующим событием, показывать предупреждение перед сохранением (не блокировать, просто предупреждать).
- [ ] Calendar: интеграция с Memory Layer — при создании события в форме, если выбранное время попадает в зону, которую пользователь ранее просил избегать (approved facts типа "не любит встречи до 10 утра"), подсвечивать предупреждение в форме создания.
- [ ] Mail: автоматическая очистка спама — фоновый агент для анализа входящих писем, классификации мусора/рекламы/уведомлений и их авто-удаления/перемещения в корзину на основе предпочтений пользователя.
- [ ] Mail: дальнейшее развитие отложено (низкий приоритет на данный момент) — индикатор непрочитанных в навигации, threading переписки, дальнейшие идеи рассмотреть позже.
- [ ] IoT: интеграция с Home Assistant (самый низкий приоритет) — вывод графиков датчиков, управление розетками/светом по командам в чате.
- [ ] Finance: добавить поле source_template_id в таблицу транзакций для надежной дедупликации (известное ограничение: сейчас два разных шаблона с абсолютно одинаковой суммой, категорией и описанием в одном месяце будут блокировать друг друга).
- [ ] Документы: умный сейф (Semantic Document Vault) — загрузка важных PDF-документов (контракты, страховки, договоры аренды), их локальное индексирование (RAG) и возможность задавать вопросы по ним в чате (например, про сроки расторжения, даты продления страховки с предложением автоматически создать дедлайны в календаре).
- [ ] Архитектура: автономное самосовершенствование (Self-Improving Agent Loop) — интеграция инструментов чтения/редактирования собственного кода, выполнение команд сборки/тестирования (npm run build, pytest) в изолированной песочнице и автономный цикл исправления ошибок (компиляции/тестов). Использовать лучшие практики и открытый код из Open Source проектов:
  - **Aider** (формат коммитов, Git-aware репозитории, эффективное редактирование через Unified Diff/Search-Replace блоки, сжатая карта проекта Repository Map).
  - **OpenHands** (бывший OpenDevin) и **SWE-agent** (песочница в Docker, интерфейс взаимодействия агента с компьютером ACI для поиска и навигации по файлам).
  - **LangGraph** и **Smolagents** (фреймворки для создания стабильных циклов рассуждений, обработки ошибок компилятора и интеграции человека в цикл одобрения изменений).


