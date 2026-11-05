import pytest

from backend.app.agent.tool_registry import dispatch_tool
from backend.app.storage import db
from backend.app.commitments.commitment_service import get_commitment


@pytest.fixture
def task_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "tasks.db"))
    db.init_db()


def _create_task(title="Send documents"):
    return dispatch_tool(
        "create_task",
        {
            "title": title,
            "deadline_at": "2030-01-10T12:00:00+00:00",
            "reminder_at": "2030-01-09T12:00:00+00:00",
        },
    )


def test_create_task_is_active_and_visible_to_task_read_model(task_db):
    result = _create_task()

    assert result["status"] == "created"
    assert result["task"]["status"] == "ACTIVE"
    assert result["task"]["approval_provenance"]["explicit_user_request"] is True

    listed = dispatch_tool("list_tasks", {})
    assert listed["status"] == "ok"
    assert [task["id"] for task in listed["tasks"]] == [result["task"]["id"]]


def test_task_can_be_rescheduled_completed_and_cancelled(task_db):
    first = _create_task("Prepare presentation")["task"]
    updated = dispatch_tool(
        "reschedule_task",
        {
            "task_id": first["id"],
            "deadline_at": "2030-01-12T15:00:00+00:00",
        },
    )
    completed = dispatch_tool("complete_task", {"task_id": first["id"]})
    second = _create_task("Cancel duplicate")["task"]
    cancelled = dispatch_tool("cancel_task", {"task_id": second["id"]})

    assert updated["status"] == "updated"
    assert updated["task"]["deadline_at"] == "2030-01-12T15:00:00+00:00"
    assert completed["status"] == "completed"
    assert completed["task"]["status"] == "COMPLETED"
    assert cancelled["status"] == "cancelled"
    assert cancelled["task"]["status"] == "CANCELLED"
    assert get_commitment(first["id"])["status"] == "COMPLETED"


def test_calendar_event_can_explicitly_link_to_task(task_db, monkeypatch):
    task = _create_task("Attend appointment")["task"]

    monkeypatch.setattr(
        "backend.app.calendar.calendar_service.create_event",
        lambda **kwargs: {"status": "created", "uid": "calendar-event-1"},
    )

    result = dispatch_tool(
        "create_event",
        {
            "title": "Appointment",
            "start_datetime": "2030-01-10T10:00:00+00:00",
            "end_datetime": "2030-01-10T11:00:00+00:00",
            "commitment_id": task["id"],
            "allow_conflicts": True,
        },
    )

    assert result["status"] == "created"
    linked = get_commitment(task["id"])
    assert linked["related_calendar_event_ids"] == ["calendar-event-1"]
    assert linked["status"] == "ACTIVE"
