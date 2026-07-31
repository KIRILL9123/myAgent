from pydantic import BaseModel, Field
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


class WebSearchArgs(BaseModel):
    query: str
    max_results: Optional[int] = 5


class WebFetchArgs(BaseModel):
    url: str
    render_js: bool = False
    browser_mode: Literal["auto", "http", "lightpanda", "chromium"] = "auto"


class SearchDocumentsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=8, ge=1, le=20)


class ListDocumentsArgs(BaseModel):
    status: Literal["active", "all", "ready", "failed", "archived"] = "active"


class HostDiagnosticsArgs(BaseModel):
    pass


class HostControlArgs(BaseModel):
    action: Literal["open_url", "open_path"]
    target: str = Field(min_length=1, max_length=2000)


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


# ─── Code sandbox models ─────────────────────────────────────────────

class SandboxSessionArgs(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)


class SandboxReadFileArgs(SandboxSessionArgs):
    path: str = Field(min_length=1, max_length=240)


class SandboxWriteFileArgs(SandboxReadFileArgs):
    content: str = Field(max_length=256 * 1024)
    overwrite: bool = False


class SandboxRunCheckArgs(SandboxReadFileArgs):
    check: Literal["python", "pytest", "node", "compile_python"] = "python"
    timeout_seconds: int = Field(default=30, ge=1, le=120)


# ─── Registry ─────────────────────────────────────────────────────────────────

TOOL_MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    "list_events": ListEventsArgs,
    "search_events": SearchEventsArgs,
    "get_weather": GetWeatherArgs,
    "web_search": WebSearchArgs,
    "web_fetch": WebFetchArgs,
    "search_documents": SearchDocumentsArgs,
    "list_documents": ListDocumentsArgs,
    "get_host_diagnostics": HostDiagnosticsArgs,
    "host_control": HostControlArgs,
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
    "sandbox_list_files": SandboxSessionArgs,
    "sandbox_read_file": SandboxReadFileArgs,
    "sandbox_write_file": SandboxWriteFileArgs,
    "sandbox_run_check": SandboxRunCheckArgs,
    "sandbox_get_diff": SandboxSessionArgs,
    "sandbox_delete_file": SandboxReadFileArgs,
    "sandbox_request_apply": SandboxSessionArgs,
}
