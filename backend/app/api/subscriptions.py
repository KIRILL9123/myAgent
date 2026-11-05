from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.connectors.mail_connector import list_unread_emails
from backend.app.api.utils import run_blocking
from backend.app.subscriptions.email_extractor import extract_email_subscriptions
from backend.app.subscriptions.subscription_service import (
    create_subscription,
    expire_overdue,
    get_subscription,
    get_subscription_events,
    list_subscriptions,
    mark_reminder_sent,
    transition_subscription,
    update_subscription,
)

router = APIRouter()


class SubscriptionCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    provider: str | None = None
    description: str | None = None
    subscription_type: str = "UNKNOWN"
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    billing_cycle: str | None = None
    trial_ends_at: str | None = None
    next_charge_at: str | None = None
    reminder_at: str | None = None
    cancellation_url: str | None = None
    cancellation_instructions: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: dict[str, Any] = Field(default_factory=dict)


class SubscriptionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    provider: str | None = None
    description: str | None = None
    subscription_type: str | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    billing_cycle: str | None = None
    trial_ends_at: str | None = None
    next_charge_at: str | None = None
    reminder_at: str | None = None
    cancellation_url: str | None = None
    cancellation_instructions: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ApprovalRequest(BaseModel):
    provenance: dict[str, Any] = Field(default_factory=dict)


class EmailSubscriptionRequest(BaseModel):
    account: str
    sender: str
    recipient: str = ""
    subject: str = ""
    date: str = ""
    preview: str = ""


class EmailScanRequest(BaseModel):
    account: str = "gmail"
    limit: int = Field(default=20, ge=1, le=100)


def _error(exc: Exception, not_found: int = 400) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc).strip("'"))
    return HTTPException(status_code=not_found, detail=str(exc))


@router.post("/")
async def api_create_subscription(req: SubscriptionCreateRequest):
    try:
        return create_subscription(**req.model_dump(), source_type="MANUAL")
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.get("/")
async def api_list_subscriptions(status: str | None = Query(default=None)):
    try:
        return {"subscriptions": list_subscriptions(status)}
    except ValueError as exc:
        raise _error(exc)


@router.get("/{subscription_id}")
async def api_get_subscription(subscription_id: str):
    subscription = get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="subscription not found")
    return subscription


@router.get("/{subscription_id}/events")
async def api_get_subscription_events(subscription_id: str):
    try:
        return {"events": get_subscription_events(subscription_id)}
    except KeyError as exc:
        raise _error(exc)


@router.patch("/{subscription_id}")
async def api_update_subscription(subscription_id: str, req: SubscriptionUpdateRequest):
    try:
        changes = {key: value for key, value in req.model_dump().items() if value is not None}
        return update_subscription(subscription_id, **changes)
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{subscription_id}/approve")
async def api_approve_subscription(subscription_id: str, req: ApprovalRequest):
    try:
        subscription = transition_subscription(subscription_id, "approve", req.provenance)
        from backend.app.finance.subscription_link_service import ensure_subscription_finance_proposal
        finance_link = ensure_subscription_finance_proposal(subscription, "web")
        return {**subscription, "finance_link": finance_link}
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{subscription_id}/cancel")
async def api_cancel_subscription(subscription_id: str):
    try:
        return transition_subscription(subscription_id, "cancel")
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{subscription_id}/reopen")
async def api_reopen_subscription(subscription_id: str):
    try:
        subscription = transition_subscription(subscription_id, "reopen")
        from backend.app.finance.subscription_link_service import ensure_subscription_finance_proposal
        finance_link = ensure_subscription_finance_proposal(subscription, "web")
        return {**subscription, "finance_link": finance_link}
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/from-email")
async def api_extract_email_subscription(req: EmailSubscriptionRequest):
    try:
        proposals = await extract_email_subscriptions(**req.model_dump())
        return {"proposals": proposals}
    except (ValueError, RuntimeError) as exc:
        raise _error(exc, 502 if isinstance(exc, RuntimeError) else 400)


@router.post("/scan-email")
async def api_scan_email_for_subscriptions(req: EmailScanRequest):
    result = await run_blocking(list_unread_emails, req.account, limit=req.limit, bypass_last_seen=True)
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=502, detail=result.get("message", "mail scan failed"))
    scanned = 0
    proposals: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for message in result:
        scanned += 1
        try:
            proposals.extend(await extract_email_subscriptions(
                account=req.account,
                sender=message.get("from", ""),
                recipient=message.get("to", ""),
                subject=message.get("subject", ""),
                date=message.get("date", ""),
                preview=message.get("preview", ""),
            ))
        except RuntimeError as exc:
            errors.append({"subject": message.get("subject", ""), "error": str(exc)})
    return {"account": req.account, "scanned": scanned, "proposals": proposals, "errors": errors}


@router.post("/maintenance/expire-overdue")
async def api_expire_overdue(now: str | None = None):
    try:
        return {"expired": expire_overdue(now)}
    except ValueError as exc:
        raise _error(exc)


@router.post("/{subscription_id}/reminder-sent")
async def api_mark_reminder_sent(subscription_id: str, sent_at: str | None = None):
    try:
        mark_reminder_sent(subscription_id, sent_at)
        return get_subscription(subscription_id)
    except (ValueError, KeyError) as exc:
        raise _error(exc)
