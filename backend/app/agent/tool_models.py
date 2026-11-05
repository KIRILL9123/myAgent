from pydantic import BaseModel, Field, model_validator
from typing import Any, Literal, Optional


# ─── Calendar models ──────────────────────────────────────────────────────────

class ListEventsArgs(BaseModel):
    start_date: str
    end_date: str


class SearchEventsArgs(BaseModel):
    query: str


class FindCalendarSlotsArgs(BaseModel):
    start_date: str
    end_date: Optional[str] = None
    duration_minutes: int = Field(default=60, ge=15, le=1440)
    earliest_time: Optional[str] = Field(default="09:00", pattern=r"^\d{1,2}(?::\d{2})?$")
    latest_time: Optional[str] = Field(default="18:00", pattern=r"^\d{1,2}(?::\d{2})?$")
    max_results: int = Field(default=5, ge=1, le=20)


class GetCalendarConflictsArgs(BaseModel):
    horizon_days: int = Field(default=30, ge=1, le=365)


TaskStatus = Literal["PROPOSED", "ACTIVE", "COMPLETED", "CANCELLED", "EXPIRED"]


class ListTasksArgs(BaseModel):
    status: Optional[TaskStatus] = None
    include_completed: bool = False


class CreateTaskArgs(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=5000)
    deadline_at: Optional[str] = None
    reminder_at: Optional[str] = None


class RescheduleTaskArgs(BaseModel):
    task_id: str = Field(min_length=1, max_length=100)
    deadline_at: str
    reminder_at: Optional[str] = None


class TaskIdArgs(BaseModel):
    task_id: str = Field(min_length=1, max_length=100)


# ── Planning and Decision Journal models ─────────────────────────────────────

GoalStatus = Literal["ACTIVE", "COMPLETED", "PAUSED", "ARCHIVED"]
ProjectStatus = Literal["PLANNED", "ACTIVE", "COMPLETED", "PAUSED", "ARCHIVED"]
DecisionStatus = Literal["ACTIVE", "REVISIT", "SUPERSEDED", "ARCHIVED"]


class CreateGoalArgs(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=5000)
    target_date: Optional[str] = None


class ListGoalsArgs(BaseModel):
    status: Optional[GoalStatus] = None


class UpdateGoalArgs(BaseModel):
    goal_id: str = Field(min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=5000)
    target_date: Optional[str] = None
    status: Optional[GoalStatus] = None


class CreateProjectArgs(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    goal_id: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: ProjectStatus = "PLANNED"
    start_date: Optional[str] = None
    target_date: Optional[str] = None


class ListProjectsArgs(BaseModel):
    status: Optional[ProjectStatus] = None
    goal_id: Optional[str] = None


class UpdateProjectArgs(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)
    goal_id: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[ProjectStatus] = None
    start_date: Optional[str] = None
    target_date: Optional[str] = None


class LinkTaskToProjectArgs(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)
    task_id: str = Field(min_length=1, max_length=100)


class CreateDecisionArgs(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    decision_text: str = Field(min_length=1, max_length=10000)
    rationale: Optional[str] = Field(default=None, max_length=10000)
    alternatives: list[str] = Field(default_factory=list, max_length=20)
    review_at: Optional[str] = None


class ListDecisionsArgs(BaseModel):
    status: Optional[DecisionStatus] = None
    query: Optional[str] = Field(default=None, max_length=200)


class RevisitDecisionArgs(BaseModel):
    decision_id: str = Field(min_length=1, max_length=100)


class GetWeatherArgs(BaseModel):
    city: str
    forecast_days: Optional[int] = Field(default=5, ge=1, le=7)


class WebSearchArgs(BaseModel):
    query: str
    max_results: Optional[int] = Field(default=5, ge=1, le=10)


class WebFetchArgs(BaseModel):
    url: str
    render_js: bool = False
    browser_mode: Literal["auto", "http", "lightpanda", "chromium"] = "auto"


class SearchDocumentsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=8, ge=1, le=20)


class ListDocumentsArgs(BaseModel):
    status: Literal["active", "all", "ready", "failed", "archived"] = "active"


class ScanDocumentProposalsArgs(BaseModel):
    document_id: int = Field(ge=1)


class ProposeDocumentActionArgs(BaseModel):
    document_id: int = Field(ge=1)
    candidate_id: str = Field(min_length=1, max_length=64)
    action_type: Literal["commitment", "calendar_event"]


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
    commitment_id: Optional[str] = None
    all_day: bool = False
    recurrence: Optional[Literal["none", "daily", "weekly", "monthly", "yearly"]] = None
    recurrence_until: Optional[str] = None
    reminder_minutes: Optional[int] = Field(default=None, ge=0)
    calendar_id: Optional[str] = None
    allow_conflicts: bool = False


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
    currency: Optional[str] = Field(default=None, pattern=r"^(?:[A-Za-z]{3}|€|\$|£|₴)$")


class GetTransactionsArgs(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None


class GetSummaryArgs(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class GetFinanceForecastArgs(BaseModel):
    months: int = Field(default=3, ge=1, le=24)
    start_date: Optional[str] = None


class AddRecurringTemplateArgs(BaseModel):
    type: TransactionType
    amount: float = Field(gt=0)
    category: str
    description: Optional[str] = None
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    frequency: Literal["weekly", "monthly", "yearly"] = "monthly"
    day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    day_of_week: Optional[int] = Field(default=None, ge=0, le=6)
    month_of_year: Optional[int] = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def validate_schedule_fields(self):
        if self.frequency == "weekly" and self.day_of_week is None:
            raise ValueError("day_of_week is required for weekly recurrence")
        if self.frequency in {"monthly", "yearly"} and self.day_of_month is None:
            raise ValueError("day_of_month is required for monthly and yearly recurrence")
        if self.frequency == "yearly" and self.month_of_year is None:
            raise ValueError("month_of_year is required for yearly recurrence")
        return self


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
