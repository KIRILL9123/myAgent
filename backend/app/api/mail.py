from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, Any

from backend.app.connectors.mail_connector import (
    list_unread_emails,
    search_emails,
    send_email
)
from backend.app.api.utils import run_api_tool

router = APIRouter()

class EmailSend(BaseModel):
    to: str
    subject: str
    body: str
    account: Optional[str] = "gmail"

@router.get("/unread")
async def api_list_unread_emails(account: str = Query("gmail")):
    return await run_api_tool(list_unread_emails, account=account, limit=10, bypass_last_seen=True)

@router.get("/search")
async def api_search_emails(query: str = Query(...), account: str = Query("gmail")):
    return await run_api_tool(search_emails, query=query, account=account, limit=10)

@router.post("/send")
async def api_send_email(email_data: EmailSend):
    return await run_api_tool(
        send_email,
        to=email_data.to,
        subject=email_data.subject,
        body=email_data.body,
        account=email_data.account
    )
