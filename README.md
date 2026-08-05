# Mira

A local-first personal AI workspace for one person. Mira brings chat, calendar,
commitments, finance, mail, memory, documents and notifications into one assistant.
It is designed to run privately on a personal computer or home server; the current
development and always-on tooling is Windows-friendly, with platform-specific
integrations documented separately.

## Status
**Current state**: Personal workspace MVP implemented across Chat, Dashboard/Today,
Calendar, Tasks/Commitments, Mail, Finance, Subscriptions, Memory, Documents,
Action Center/Notifications, Scheduler, Telegram parity and the Code Sandbox.

## Prerequisites

- **Python 3.11+**
   *   On Windows, create the environment with `py -3.11 -m venv .venv` and activate it with `.\.venv\Scripts\Activate.ps1`.
   *   On macOS/Linux, use `python3.11 -m venv .venv` (or a manager such as `pyenv` or `uv`).
- **Node.js & npm** (tested on Node v20/v22) for the frontend dashboard.
- **A local model server** configured in `.env` (Ollama is supported; an OpenAI-compatible local provider can also be configured).
- **FFmpeg** installed on the host system (required for processing and transcribing Telegram audio messages).
  *   On macOS, install via: `brew install ffmpeg`

## Setup

1. **Clone the repository** (or copy to your home directory):
   ```bash
   git clone <repository_url> mira
   cd mira
   ```

2. **Create and configure the Python virtual environment**:
   Create the virtual environment using Python 3.11+ and install Python dependencies.
   On Windows PowerShell:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
   On macOS/Linux, use `python3.11 -m venv .venv`, `source .venv/bin/activate`,
   then run the same `pip` and Playwright commands.

3. **Configure the local model server**:
   If using Ollama, install it separately and pull the configured model:
   ```bash
   ollama pull qwen2.5:7b
   ```
   An OpenAI-compatible local provider can be used instead by configuring its endpoint
   and model in `.env`.

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and populate your secrets:
   ```bash
   cp .env.example .env
   ```
   In PowerShell, use `Copy-Item .env.example .env` instead.
   The example is intentionally safe for a personal local installation: it uses the
   local calendar, starts in `dry_run`, disables subscription email scans, and leaves
   the API key empty. Keep those defaults while testing; explicitly change only the
   integrations you personally want to use.
   *Instructions for each section in `.env`:*
   - **iCloud CalDAV**: Create an App-Specific Password at [appleid.apple.com](https://appleid.apple.com) and enter it in `CALDAV_PASSWORD`.
   - **Gmail**: If using Gmail, create a Google App-Specific Password at [myaccount.google.com](https://myaccount.google.com) (requires 2FA enabled on your Google account) and enter it in `GMAIL_APP_PASSWORD`.
   - **UkrNet**: Enable IMAP/SMTP in your UkrNet mailbox settings, generate a third-party application password, and enter it in `UKRNET_PASSWORD`.
   - **Telegram**: Create a bot via `@BotFather` to get `TELEGRAM_BOT_TOKEN`, and find your chat ID using `@userinfobot` to set `TELEGRAM_CHAT_ID`.
   - **FastAPI Security Key**: Generate a secure 32-byte key for `HOME_AGENT_API_KEY` by running:
     ```bash
     python3 -c "import secrets; print(secrets.token_hex(32))"
     ```

5. **Configure the Frontend API Key**:
   The frontend must know the same API key as the backend in order to authenticate all requests:
   ```bash
   cp frontend/.env.example frontend/.env
   ```
   In PowerShell, use `Copy-Item frontend/.env.example frontend/.env` instead.
   Open `frontend/.env` and set `VITE_API_KEY` to the same value you used for `HOME_AGENT_API_KEY` in the backend `.env`.

6. **Build the Frontend (Mandatory for Web Dashboard)**:
   Navigate to the frontend directory, install dependencies, and build the static assets. This step must be run before starting the backend if you wish to access the web panel:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
   *Note*: The production assets are generated in `frontend/dist/` and served automatically by the FastAPI backend.

7. **Start the Application**:
   Launch the FastAPI web server from the project root:
   ```bash
   powershell -ExecutionPolicy Bypass -File .\dev-tools\start_backend.ps1
   ```
   The start script checks port 8000 first and stops with an explicit PID message if an old backend is already listening; it never terminates another process automatically. The server will initialize the SQLite database and run any missing migrations automatically on startup. The web dashboard will be available at [http://localhost:8000/dashboard](http://localhost:8000/dashboard) (with `/memory` and other modules routed inside the SPA).

## Development

If you are developing the React interface and want Hot Module Replacement (HMR):
1. Keep the backend server running.
2. In a separate terminal, run:
   ```bash
   cd frontend
   npm run dev
   ```
   This will start the Vite dev server at [http://localhost:5173/dashboard](http://localhost:5173/dashboard) and proxy API requests automatically to the backend.

## Testing

Run the automated test suite:
```bash
pytest
```
This runs 170+ tests covering tool validation, dry-run safety, permissions, memory lifecycle, API security, and more. Tests use isolated temporary databases and mocked external services — no real credentials or network access required.

CI runs automatically on push/PR via GitHub Actions.

See [docs/TESTING.md](docs/TESTING.md) for details on test architecture and fixtures.

## Architecture & Design
See [PRODUCT_ARCHITECTURE.md](PRODUCT_ARCHITECTURE.md) for product boundaries,
[ARCHITECTURE.md](docs/ARCHITECTURE.md) for runtime architecture,
[OPERATIONS.md](docs/OPERATIONS.md) for running the project,
[SECURITY_AND_SAFETY.md](docs/SECURITY_AND_SAFETY.md) for safety contracts,
and [ROADMAP.md](docs/ROADMAP.md) plus [BACKLOG.md](docs/BACKLOG.md) for future work.

## Project Documents

- [Master vision alignment](docs/MASTER_VISION_ALIGNMENT.md)
- [Operations and reliability](docs/OPERATIONS.md)
- [Security and safety](docs/SECURITY_AND_SAFETY.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Product architecture](PRODUCT_ARCHITECTURE.md)
- [Feature proposal template](docs/templates/FEATURE_PROPOSAL.md)
- [Provenance and evidence bundle](docs/design/PROVENANCE_BUNDLE.md)
- [Long-term roadmap](docs/ROADMAP.md)
- [Active backlog](docs/BACKLOG.md)
- [Commitment contract](docs/domain/COMMITMENT_CONTRACT.md)
- [Memory evolution design](docs/design/MEMORY_EVOLUTION.md)
- [Decision log](docs/decisions/DECISION_LOG.md)
- [Open-source integrations](docs/decisions/OSS_INTEGRATIONS.md)
