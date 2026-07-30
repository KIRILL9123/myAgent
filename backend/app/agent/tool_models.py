from pydantic import BaseModel
from typing import Any, Literal, Optional


# ─── Calendar models ──────────────────────────────────────────────────────────

class ListEventsArgs(BaseModel):
    start_date: str
    end_date: str


class SearchEventsArgs(BaseModel):
    query: str


class GetWeatherArgs(BaseModel):
    city: str
    forecast_days: Optional[int] = 5


class CreateEventArgs(BaseModel):
    title: str
    start_datetime: str
    end_datetime: Optional[str] = None
    description: Optional[str] = None


class DeleteEventArgs(BaseModel):
    event_uid: str


class ModifyEventArgs(BaseModel):
    event_uid: str
    updated_fields: dict[str, Any]


# ─── Mail models ──────────────────────────────────────────────────────────────

MailAccount = Literal["gmail", "ukrnet"]


class ListUnreadEmailsArgs(BaseModel):
    account: MailAccount
    limit: Optional[int] = None


class SearchEmailsArgs(BaseModel):
    account: MailAccount
    query: str


class SendEmailArgs(BaseModel):
    to: str
    subject: str
    body: str
    account: Optional[MailAccount] = None


# ─── Finance models ───────────────────────────────────────────────────────────

TransactionType = Literal["income", "expense"]


class AddTransactionArgs(BaseModel):
    type: TransactionType
    amount: float
    category: str
    description: Optional[str] = None
    date: Optional[str] = None


class GetTransactionsArgs(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None


class GetSummaryArgs(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ─── Countdown models ─────────────────────────────────────────────────────────

class AddCountdownArgs(BaseModel):
    title: str
    target_date: str
    category: Optional[str] = None


class GetAllCountdownsArgs(BaseModel):
    pass


class DeleteCountdownArgs(BaseModel):
    countdown_id: int


# ─── Registry ─────────────────────────────────────────────────────────────────

TOOL_MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    "list_events": ListEventsArgs,
    "search_events": SearchEventsArgs,
    "get_weather": GetWeatherArgs,
    "create_event": CreateEventArgs,
    "modify_event": ModifyEventArgs,
    "delete_event": DeleteEventArgs,
    "list_unread_emails": ListUnreadEmailsArgs,
    "search_emails": SearchEmailsArgs,
    "send_email": SendEmailArgs,
    "add_transaction": AddTransactionArgs,
    "get_transactions": GetTransactionsArgs,
    "get_summary": GetSummaryArgs,
    "add_countdown": AddCountdownArgs,
    "get_all_countdowns": GetAllCountdownsArgs,
    "delete_countdown": DeleteCountdownArgs,
}
