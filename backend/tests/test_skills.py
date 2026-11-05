import pytest

from backend.app.approvals.approval_service import list_approvals, resolve_approval
from backend.app.memory.skill_service import create_skill, list_skills, select_skills
from backend.app.storage import db


@pytest.fixture
def skills_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "skills.db"))
    db.init_db()


@pytest.mark.asyncio
async def test_user_skill_is_approval_gated_and_selectable(skills_db):
    created = create_skill(
        "german_research",
        "Use German sources for shopping research.",
        ["german research", "deutsche preise"],
        ["Use German sources first.", "Show prices in EUR."],
        category="research",
    )
    assert created["status"] == "draft"
    assert created["approval_id"]
    assert select_skills("german research") == []

    pending = list_approvals()
    request = next(item for item in pending if item["kind"] == "SKILL")
    resolved = await resolve_approval(request["id"], "approve", "Проверено")
    assert resolved["status"] == "APPROVED"
    assert any(skill["name"] == "german_research" for skill in select_skills("german research"))


def test_builtin_skills_are_approved_and_draft_skills_are_hidden(skills_db):
    skills = list_skills("approved")
    assert skills
    assert all(skill["status"] == "approved" for skill in skills)
    assert any(skill["source"] == "builtin" for skill in skills)
