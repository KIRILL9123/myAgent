import asyncio
from backend.app.agent.scheduled_tasks import morning_summary

if __name__ == "__main__":
    asyncio.run(morning_summary())
