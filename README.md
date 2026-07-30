# Home Agent

A local AI agent running 24/7 on a Mac as a home server, designed to manage daily routines (calendar, email, and eventually smart home). It's accessible locally via Wi-Fi and remotely via Tailscale.

## Status
**Current state**: Multi-module MVP implemented (chat, calendar, mail, finance, countdowns, memory, scheduler).

## Prerequisites

- **Python 3.11+**
  *   *Note for macOS users*: The default system `python3` command points to an older version (e.g., Python 3.9.x). You must explicitly create your virtual environment using `python3.11 -m venv .venv` (or use a manager like `pyenv` or `uv`). Do NOT use `python3 -m venv .venv` if your default python3 version is older than 3.11, as the modern type union operators (`|`) used in the codebase will crash on startup.
- **Node.js & npm** (tested on Node v20/v22) for the frontend dashboard.
- **Ollama** installed separately (https://ollama.com) and running locally.
- **FFmpeg** installed on the host system (required for processing and transcribing Telegram audio messages).
  *   On macOS, install via: `brew install ffmpeg`

## Setup

1. **Clone the repository** (or copy to your home directory):
   ```bash
   git clone <repository_url> home-agent
   cd home-agent
   ```

2. **Create and configure the Python virtual environment**:
   Create the virtual environment using Python 3.11+ and install Python dependencies:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install Ollama Model**:
   Pull the target model used by the LLM client:
   ```bash
   ollama pull qwen2.5:7b
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and populate your secrets:
   ```bash
   cp .env.example .env
   ```
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

6. **Start the Application**:
   Launch the FastAPI web server from the project root:
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```
   The server will initialize the SQLite database and run any missing migrations automatically on startup. The web dashboard will be available at [http://localhost:8000/dashboard](http://localhost:8000/dashboard) (with `/memory` and other modules routed inside the SPA).

## Development

If you are developing the React interface and want Hot Module Replacement (HMR):
1. Keep the backend server running.
2. In a separate terminal, run:
   ```bash
   cd frontend
   npm run dev
   ```
   This will start the Vite dev server at [http://localhost:5173/dashboard](http://localhost:5173/dashboard) and proxy API requests automatically to the backend.

## Architecture & Design
See [ARCHITECTURE.md](docs/ARCHITECTURE.md) and [ROADMAP.md](docs/ROADMAP.md) for deeper details.

## Project Documents

- [Master vision alignment](docs/MASTER_VISION_ALIGNMENT.md)
- [Operations and reliability](docs/OPERATIONS.md)
- [Security and safety](docs/SECURITY_AND_SAFETY.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Long-term roadmap](docs/ROADMAP.md)
- [Active backlog](docs/BACKLOG.md)
- [Commitment contract](docs/domain/COMMITMENT_CONTRACT.md)
- [Memory evolution design](docs/design/MEMORY_EVOLUTION.md)
- [Decision log](docs/decisions/DECISION_LOG.md)
