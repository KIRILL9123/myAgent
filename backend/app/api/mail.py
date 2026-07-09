from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any
import asyncio

from backend.app.connectors.mail_connector import (
    list_unread_emails,
    search_emails,
    send_email
)

router = APIRouter()

class EmailSend(BaseModel):
    to: str
    subject: str
    body: str
    account: Optional[str] = "gmail"

@router.get("/unread")
async def api_list_unread_emails(account: str = Query("gmail")):
    try:
        emails = await asyncio.to_thread(list_unread_emails, account=account, limit=10, bypass_last_seen=True)
        if emails and isinstance(emails, list) and len(emails) > 0 and isinstance(emails[0], dict) and "error" in emails[0]:
            raise HTTPException(status_code=400, detail=emails[0]["error"])
        return emails
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def api_search_emails(query: str = Query(...), account: str = Query("gmail")):
    try:
        emails = await asyncio.to_thread(search_emails, query=query, account=account, limit=10)
        if emails and isinstance(emails, list) and len(emails) > 0 and isinstance(emails[0], dict) and "error" in emails[0]:
            raise HTTPException(status_code=400, detail=emails[0]["error"])
        return emails
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send")
async def api_send_email(email_data: EmailSend):
    try:
        result = await asyncio.to_thread(
            send_email,
            to=email_data.to,
            subject=email_data.subject,
            body=email_data.body,
            account=email_data.account or "gmail"
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
