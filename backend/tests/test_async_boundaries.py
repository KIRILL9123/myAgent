import threading

import pytest

from backend.app.api.utils import run_blocking


@pytest.mark.asyncio
async def test_run_blocking_moves_sync_work_off_event_loop_thread():
    event_loop_thread = threading.get_ident()

    worker_thread = await run_blocking(threading.get_ident)

    assert worker_thread != event_loop_thread
