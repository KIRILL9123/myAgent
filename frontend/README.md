# Mira — Frontend

React + TypeScript + Vite dashboard for the Mira personal assistant backend.

## Stack

- **React 19** with React Router v7 for client-side routing
- **TypeScript** (strict, compiled via `tsc` before production build)
- **Vite 8** for dev server and bundling
- **Tailwind CSS v4** (via `@tailwindcss/vite` plugin)
- **Recharts** for finance charts
- **react-force-graph-2d** for the memory knowledge graph
- **lucide-react** for icons

## Structure

```
frontend/src/
  api/           # Typed API clients (chat, calendar, mail, finance, memory, countdown)
  components/    # Shared UI components (AppShell, MemoryGraph, PendingFactsQueue, ConsolidationQueue)
  pages/         # One file per route (Dashboard, Chat, Calendar, Mail, Finance, Countdowns, Memory)
  main.tsx       # App entry point and router setup
  index.css      # Global styles (Tailwind base)
```

All API calls include the `X-API-Key` header sourced from `VITE_API_KEY` in `frontend/.env`.

## Development

Start the FastAPI backend first (port 8000), then:

```bash
cd frontend
npm install
npm run dev       # Vite dev server at http://localhost:5173 — proxies /api/* to localhost:8000
```

## Production build

```bash
cd frontend
npm install
npm run build     # tsc -b && vite build → outputs to frontend/dist/
```

The FastAPI backend serves the built `frontend/dist/` directory as static files. Run the build before starting the backend if you want the web dashboard available.

## Linting

```bash
npm run lint      # oxlint
```
