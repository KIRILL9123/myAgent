from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.planning.planning_service import (
    create_goal, create_project, link_task_to_project, list_goals, list_project_tasks,
    list_projects, update_goal, update_project,
)

router = APIRouter()


class GoalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    target_date: str | None = None
    status: str = "ACTIVE"
    provenance: dict[str, Any] = Field(default_factory=dict)


class GoalUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    target_date: str | None = None
    status: str | None = None


class ProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    goal_id: str | None = None
    description: str | None = Field(default=None, max_length=5000)
    status: str = "PLANNED"
    start_date: str | None = None
    target_date: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    goal_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    start_date: str | None = None
    target_date: str | None = None


class ProjectTaskRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=100)


def _error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404 if isinstance(exc, KeyError) else 400, detail=str(exc).strip("'"))


@router.get("/goals")
async def api_list_goals(status: str | None = Query(default=None)):
    try:
        return {"goals": list_goals(status)}
    except ValueError as exc:
        raise _error(exc)


@router.post("/goals")
async def api_create_goal(req: GoalRequest):
    try:
        return create_goal(**req.model_dump())
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.patch("/goals/{goal_id}")
async def api_update_goal(goal_id: str, req: GoalUpdateRequest):
    try:
        return update_goal(goal_id, **{key: value for key, value in req.model_dump().items() if value is not None})
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.get("/projects")
async def api_list_projects(status: str | None = Query(default=None), goal_id: str | None = Query(default=None)):
    try:
        return {"projects": list_projects(status, goal_id)}
    except ValueError as exc:
        raise _error(exc)


@router.post("/projects")
async def api_create_project(req: ProjectRequest):
    try:
        return create_project(**req.model_dump())
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.patch("/projects/{project_id}")
async def api_update_project(project_id: str, req: ProjectUpdateRequest):
    try:
        return update_project(project_id, **{key: value for key, value in req.model_dump().items() if value is not None})
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.get("/projects/{project_id}/tasks")
async def api_list_project_tasks(project_id: str):
    try:
        return {"tasks": list_project_tasks(project_id)}
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/projects/{project_id}/tasks")
async def api_link_task(project_id: str, req: ProjectTaskRequest):
    try:
        return link_task_to_project(project_id, req.task_id)
    except (ValueError, KeyError) as exc:
        raise _error(exc)
