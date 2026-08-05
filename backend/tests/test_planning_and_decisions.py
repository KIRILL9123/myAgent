import pytest

from backend.app.agent.tool_registry import dispatch_tool, get_tool_spec
from backend.app.memory.decision_service import list_decisions
from backend.app.planning.planning_service import list_project_tasks
from backend.app.storage import db


@pytest.fixture
def planning_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "planning.db"))
    db.init_db()


def test_goals_projects_and_existing_tasks_share_one_hierarchy(planning_db):
    goal = dispatch_tool("create_goal", {"title": "Launch personal dashboard", "target_date": "2030-06-01"})["goal"]
    project = dispatch_tool("create_project", {"title": "Calendar polish", "goal_id": goal["id"], "target_date": "2030-05-01"})["project"]
    task = dispatch_tool("create_task", {"title": "Review calendar layout"})["task"]
    linked = dispatch_tool("link_task_to_project", {"project_id": project["id"], "task_id": task["id"]})

    assert project["goal_id"] == goal["id"]
    assert linked["task"]["project_id"] == project["id"]
    assert list_project_tasks(project["id"])[0]["id"] == task["id"]
    assert dispatch_tool("list_projects", {"goal_id": goal["id"]})["projects"][0]["id"] == project["id"]


def test_decision_journal_is_explicit_and_available_in_shared_registry(planning_db):
    created = dispatch_tool("create_decision", {
        "title": "Keep local-first storage",
        "decision_text": "Use SQLite until a real multi-device need appears.",
        "rationale": "The project is personal and offline-friendly.",
        "review_at": "2030-01-01T12:00:00+00:00",
    })["decision"]
    assert created["source_type"] == "CHAT"
    assert dispatch_tool("list_decisions", {"query": "local-first"})["decisions"][0]["id"] == created["id"]
    revisited = dispatch_tool("revisit_decision", {"decision_id": created["id"]})["decision"]
    assert revisited["status"] == "REVISIT"
    assert list_decisions(status="REVISIT")[0]["id"] == created["id"]


def test_chat_and_telegram_use_the_same_new_tool_specs():
    for name in ("create_goal", "create_project", "create_decision"):
        spec = get_tool_spec(name)
        assert spec is not None
        assert spec.permission.value == "green"
