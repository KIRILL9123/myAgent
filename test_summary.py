import asyncio
import sys
sys.path.insert(0, ".")
from backend.app.agent.scheduled_tasks import morning_summary

asyncio.run(morning_summary())
