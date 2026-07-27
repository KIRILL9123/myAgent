# Architecture

> Note: parts of this document are historical. For code-accurate status, see [ARCHITECTURE_STATUS.md](ARCHITECTURE_STATUS.md).

## Overview

The Home Agent is structured with a FastAPI backend driving an orchestration loop, connecting to local LLMs (Ollama) and external services (CalDAV, IMAP, and eventually Home Assistant).

## Data Flow

1. **Input**: User sends a request via `/chat` endpoint (REST/WebSocket) or via Telegram Bot message.
2. **Listener**: `telegram_listener.py` intercepts Telegram messages using long-polling, validating `TELEGRAM_CHAT_ID` before routing.
3. **Orchestrator**: The central agent loop receives the request and builds a system prompt containing the available tools and conversation history.
3. **LLM**: The system prompt and user input are sent to the local Ollama instance via `llm_client.py`.
4. **Tool Selection**: The LLM decides if a tool call is needed and returns a structured response.
5. **Permission Check**: The orchestrator intercepts the tool call and passes it to `permission_checker.py`.
    - **Green/Yellow**: Execution proceeds immediately.
    - **Red**: The action is stored as pending and the user is asked for explicit confirmation.
6. **Execution**: The tool (e.g., `caldav_connector.py`, `mail_connector.py`) interacts with the external service.
7. **Audit**: The action is logged to `audit_log.py`, including PENDING_CONFIRMATION → CONFIRMED/CANCELLED for red actions.
8. **Response**: The result is fed back to the LLM to formulate the final answer to the user.
## Frontend Modules

The frontend is structured as a multi-module dashboard built with React + TypeScript + Vite.
- **Chat**: The core interface for communicating with the agent.
- **Finance**: A dedicated module for tracking incomes, expenses, and viewing summaries.
- **Deadlines**: A module for tracking countdowns to important dates.
- Future modules will be added here as the application grows.

## Layers

- **API Layer**: `fastapi` entrypoints for client communication.
- **Agent Layer**: Core intelligence, tool calling loops, session-based memory for confirmations.
  - **Memory Sublayer**: custom SQLite-backed Memory Layer (`backend/app/memory/*`) with human approval flow, relation graphing, and consolidation support.
- **Permission Layer**: Hardcoded, strictly enforced security boundaries (`tool_permissions.json`).
- **Voice Sublayer**: `transcriber.py` uses `openai-whisper` for local speech-to-text recognition.
- **Connector Layer**: Adapters for third-party services:
  - `caldav_connector.py` — iCloud Calendar (read + write)
  - `mail_connector.py` — IMAP (read) and SMTP (write) for multiple accounts (Gmail, Ukrnet)
- **Background Layer**: 
  - `scheduled_tasks.py` — APScheduler cron jobs for proactive tasks (e.g. morning summary)
  - `telegram_notifier.py` — Push notifications to Telegram
