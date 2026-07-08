# Home Agent

A local AI agent running 24/7 on a Mac as a home server, designed to manage daily routines (calendar, email, and eventually smart home). It's accessible locally via Wi-Fi and remotely via Tailscale.

## Status
**Phase 1 (Foundation)**: Active

## Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed locally (running on `localhost:11434`)

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   ```

3. Run the application:
   ```bash
   uvicorn backend.app.main:app --reload
   ```

## Architecture
See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Roadmap
See [ROADMAP.md](docs/ROADMAP.md) for future phases.

## Frontend Setup (Vite + React + Tailwind)

The frontend is located in the `frontend/` directory.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```
   By default, the dev server will run on [http://localhost:5173/memory](http://localhost:5173/memory).

4. Build for production:
   ```bash
   npm run build
   ```
   This will compile assets into `frontend/dist/`, which are automatically served by the FastAPI backend at [http://localhost:8000](http://localhost:8000) when running the uvicorn server.
