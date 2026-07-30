import os
import time
from uuid import UUID
from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from backend.app.api.chat import router as chat_router
from backend.app.agent.scheduled_tasks import morning_summary
from backend.app.observability.telemetry import (
    elapsed_ms, new_correlation_id, record_event, reset_correlation_id,
    set_correlation_id,
)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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
        replace_existing=True,
        misfire_grace_time=21600
    )

    from backend.app.memory.memory_service import run_scheduled_consolidation
    scheduler.add_job(
        run_scheduled_consolidation,
        trigger=CronTrigger(hour=3, minute=0),
        id="nightly_consolidation_job",
        replace_existing=True,
        misfire_grace_time=21600
    )

    from backend.app.finance.finance_service import process_recurring_transactions
    scheduler.add_job(
        process_recurring_transactions,
        trigger=CronTrigger(hour=1, minute=0),
        id="recurring_transactions_job",
        replace_existing=True,
        misfire_grace_time=21600
    )

    async def commitment_reminder_job():
        from backend.app.commitments.commitment_service import get_due_reminders, mark_reminder_sent
        from backend.app.notifications.telegram_notifier import send_notification

        for commitment in get_due_reminders():
            deadline = commitment.get("deadline_at") or "без указанного срока"
            message = f"Напоминание об обязательстве:\n{commitment['title']}\nСрок: {deadline}"
            result = await send_notification(message)
            if result is True:
                mark_reminder_sent(commitment["id"])

    scheduler.add_job(
        commitment_reminder_job,
        trigger=IntervalTrigger(minutes=15),
        id="commitment_reminder_job",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    from backend.app.storage.backup import create_backup, apply_retention_policy

    async def daily_backup_job():
        import asyncio
        result = await asyncio.to_thread(create_backup)
        if result.get("status") == "ok":
            apply_retention_policy()

    scheduler.add_job(
        daily_backup_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_backup_job",
        replace_existing=True,
        misfire_grace_time=21600
    )

    scheduler.start()
    print(f"[SCHEDULER] Started. Morning summary at {hour:02d}:{minute:02d}, consolidation at 03:00")
    
    import asyncio
    from backend.app.notifications.telegram_listener import start_polling
    telegram_task = asyncio.create_task(start_polling())
    _background_tasks.add(telegram_task)
    telegram_task.add_done_callback(_background_tasks.discard)
    telegram_task.add_done_callback(_log_task_exception)
    yield
    
    telegram_task.cancel()
    scheduler.shutdown()
    print("[SCHEDULER] Shutdown.")
    
    from backend.app.agent.llm import close_http_client
    await close_http_client()
    print("[LLM CLIENT] Closed HTTP client pool.")

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
async def observability_middleware(request: Request, call_next: Any) -> Response:
    incoming = request.headers.get("X-Correlation-ID", "").strip()
    try:
        UUID(incoming)
        correlation_id = incoming
    except (ValueError, AttributeError):
        correlation_id = new_correlation_id()
    token = set_correlation_id(correlation_id)
    started = time.monotonic()
    response: Response | None = None
    status = "success"
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        status = "success" if status_code < 400 else ("4xx" if status_code < 500 else "5xx")
        return response
    except Exception:
        status = "error"
        raise
    finally:
        record_event("http_request", "api", status, elapsed_ms(started),
                     {"method": request.method, "path": request.url.path,
                      "status_code": status_code})
        if response is not None:
            response.headers["X-Correlation-ID"] = correlation_id
        reset_correlation_id(token)


@app.middleware("http")
async def api_key_auth_middleware(request: Request, call_next: Any) -> Response:
    # Bypass CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path.startswith("/api"):
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

from backend.app.api.commitments import router as commitments_router
app.include_router(commitments_router, prefix="/api/commitments")

from backend.app.api.approvals import router as approvals_router
app.include_router(approvals_router, prefix="/api/approvals")

from backend.app.api.system import router as system_router
app.include_router(system_router, prefix="/api/system")

from fastapi.staticfiles import StaticFiles


from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, JSONResponse

@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request: Request, exc: StarletteHTTPException) -> Response:
    if exc.status_code == 404:
        if not request.url.path.startswith("/api"):
            index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist", "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            else:
                return JSONResponse(
                    status_code=404,
                    content={"detail": "Web dashboard is not built. Run 'npm run build' in the frontend/ directory to serve the dashboard. API endpoints will work regardless."}
                )
    return await http_exception_handler(request, exc)

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "Home Agent is running"}

# Gracefully mount frontend static files if they exist
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
else:
    import logging
    logging.warning(
        "WARNING: frontend/dist not found — run 'npm run build' in frontend/ to serve the web dashboard. API endpoints will work regardless."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

