import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.app.api.chat import router as chat_router
from backend.app.agent.scheduled_tasks import morning_summary

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup scheduler
    summary_time = os.getenv("MORNING_SUMMARY_TIME", "08:00")
    try:
        hour, minute = map(int, summary_time.split(":"))
    except ValueError:
        hour, minute = 8, 0

    from backend.app.storage.db import init_db
    init_db()
    print("[DB] Initialized database.")

    scheduler.add_job(
        morning_summary,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="morning_summary_job",
        replace_existing=True
    )

    from backend.app.memory.memory_service import run_scheduled_consolidation
    scheduler.add_job(
        run_scheduled_consolidation,
        trigger=CronTrigger(hour=3, minute=0),
        id="nightly_consolidation_job",
        replace_existing=True
    )

    from backend.app.finance.finance_service import process_recurring_transactions
    scheduler.add_job(
        process_recurring_transactions,
        trigger=CronTrigger(hour=1, minute=0),
        id="recurring_transactions_job",
        replace_existing=True
    )

    scheduler.start()
    print(f"[SCHEDULER] Started. Morning summary at {hour:02d}:{minute:02d}, consolidation at 03:00")
    
    import asyncio
    from backend.app.notifications.telegram_listener import start_polling
    telegram_task = asyncio.create_task(start_polling())
    _background_tasks.add(telegram_task)
    telegram_task.add_done_callback(_background_tasks.discard)
    telegram_task.add_done_callback(_log_task_exception)
    print("[TELEGRAM] Listener background task started.")
    
    yield
    
    telegram_task.cancel()
    scheduler.shutdown()
    print("[SCHEDULER] Shutdown.")

_background_tasks: set = set()

def _log_task_exception(task):
    try:
        exception = task.exception()
        if exception:
            import logging
            logging.error(f"Background Telegram listener task failed: {exception}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        import logging
        logging.error(f"Error checking Telegram listener task exception: {e}")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Home Agent API",
    description="Local AI agent managing routines",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def api_key_auth_middleware(request: Request, call_next):
    # Bypass CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path.startswith("/api"):
        if request.url.path == "/api/health":
            return await call_next(request)

        api_key = os.getenv("HOME_AGENT_API_KEY")
        if not api_key:
            return JSONResponse(
                status_code=500,
                content={"detail": "HOME_AGENT_API_KEY is not configured on the server."}
            )

        header_key = request.headers.get("X-API-Key")
        if header_key != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Invalid or missing API Key."}
            )

    return await call_next(request)

app.include_router(chat_router, prefix="/api")

from backend.app.api.finance import router as finance_router
app.include_router(finance_router, prefix="/api/finance")

from backend.app.countdown.countdown_routes import router as countdown_router
app.include_router(countdown_router, prefix="/api/countdown")

from backend.app.api.memory import router as memory_router
app.include_router(memory_router, prefix="/api/memory")

from backend.app.api.calendar import router as calendar_router
app.include_router(calendar_router, prefix="/api/calendar")

from backend.app.api.mail import router as mail_router
app.include_router(mail_router, prefix="/api/mail")

from fastapi.staticfiles import StaticFiles

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse

@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request, exc):
    if exc.status_code == 404:
        if not request.url.path.startswith("/api"):
            index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist", "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
    return await http_exception_handler(request, exc)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Home Agent is running"}

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
