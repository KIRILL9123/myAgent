"""Storage and deterministic selection for approved procedural skills."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.app.storage.db import get_db_connection


BUILTIN_SKILLS = (
    {
        "name": "euro_price_research",
        "description": "Исследование цен для Германии и отображение сумм в евро.",
        "triggers": ["цена", "стоимость", "купить", "price", "cost", "buy"],
        "steps": [
            "Учитывай Германию как регион, если пользователь не указал другой.",
            "Сравнивай несколько актуальных источников и указывай дату проверки.",
            "Показывай денежные суммы в евро, не в рублях.",
        ],
        "category": "research",
    },
    {
        "name": "safe_email_workflow",
        "description": "Безопасная подготовка и отправка email.",
        "triggers": ["отправь письмо", "ответь на письмо", "send email", "reply email"],
        "steps": [
            "Проверь получателя и тему по исходному письму.",
            "Для отправки используй send_email и дождись встроенного RED-подтверждения.",
            "Не сообщай об отправке, пока инструмент не вернул успешный результат.",
        ],
        "category": "safety",
    },
    {
        "name": "sandbox_code_workflow",
        "description": "Безопасный цикл создания и проверки кода.",
        "triggers": ["напиши код", "создай файл", "write code", "create file", "реализуй"],
        "steps": [
            "Для нового кода используй изолированную песочницу.",
            "После изменений сначала покажи diff и запусти разрешённые проверки.",
            "Применение изменений к основному проекту требует отдельного подтверждения.",
        ],
        "category": "safety",
    },
)


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    try:
        parsed = json.loads(value) if value else default
        return parsed
    except json.JSONDecodeError:
        return default


def _row_to_skill(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "id", "name", "description", "triggers_json", "steps_json", "category",
        "source", "status", "version", "use_count", "last_used_at", "created_at", "updated_at",
    )
    result = dict(zip(keys, row))
    result["triggers"] = _loads(result.pop("triggers_json"), [])
    result["steps"] = _loads(result.pop("steps_json"), [])
    return result


def ensure_builtin_skills() -> None:
    with get_db_connection() as conn:
        for skill in BUILTIN_SKILLS:
            conn.execute(
                """INSERT OR IGNORE INTO procedural_skills
                   (name, description, triggers_json, steps_json, category, source, status)
                   VALUES (?, ?, ?, ?, ?, 'builtin', 'approved')""",
                (skill["name"], skill["description"], _json(skill["triggers"]), _json(skill["steps"]), skill["category"]),
            )
        conn.commit()


def list_skills(status: str = "approved") -> list[dict[str, Any]]:
    ensure_builtin_skills()
    with get_db_connection() as conn:
        if status == "all":
            rows = conn.execute(
                """SELECT id, name, description, triggers_json, steps_json, category,
                          source, status, version, use_count, last_used_at, created_at, updated_at
                   FROM procedural_skills ORDER BY status, name"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, name, description, triggers_json, steps_json, category,
                          source, status, version, use_count, last_used_at, created_at, updated_at
                   FROM procedural_skills WHERE status = ? ORDER BY name""",
                (status,),
            ).fetchall()
    return [_row_to_skill(row) for row in rows]


def get_skill(skill_id: int) -> dict[str, Any] | None:
    ensure_builtin_skills()
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT id, name, description, triggers_json, steps_json, category,
                      source, status, version, use_count, last_used_at, created_at, updated_at
               FROM procedural_skills WHERE id = ?""",
            (skill_id,),
        ).fetchone()
    return _row_to_skill(row) if row else None


def create_skill(
    name: str,
    description: str,
    triggers: list[str],
    steps: list[str],
    category: str = "general",
    source_channel: str = "web",
) -> dict[str, Any]:
    clean_name = re.sub(r"[^\w\-]+", "_", name.casefold(), flags=re.UNICODE).strip("_-")
    if not clean_name:
        raise ValueError("skill name must contain latin letters, numbers, _ or -")
    clean_triggers = sorted({item.strip().casefold() for item in triggers if item.strip()})[:20]
    clean_steps = [item.strip() for item in steps if item.strip()][:20]
    if not clean_triggers or not clean_steps:
        raise ValueError("skill requires at least one trigger and one step")
    with get_db_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO procedural_skills
               (name, description, triggers_json, steps_json, category, source, status)
               VALUES (?, ?, ?, ?, ?, 'user', 'draft')""",
            (clean_name, description.strip(), _json(clean_triggers), _json(clean_steps), category.strip() or "general"),
        )
        skill_id = int(cursor.lastrowid)
        conn.commit()

    from backend.app.approvals.approval_service import _upsert_request
    approval_id = _upsert_request(
        "SKILL", str(skill_id), f"Подтвердить навык: {clean_name}",
        description.strip() or "Новый процедурный навык требует подтверждения.",
        {"skill_id": skill_id, "name": clean_name, "triggers": clean_triggers, "steps": clean_steps, "category": category},
        source_channel,
    )
    result = get_skill(skill_id) or {}
    result["approval_id"] = approval_id
    return result


def approve_skill(skill_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "UPDATE procedural_skills SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'draft'",
            (skill_id,),
        )
        conn.commit()
    return cursor.rowcount > 0


def disable_skill(skill_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "UPDATE procedural_skills SET status = 'disabled', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status IN ('draft', 'approved')",
            (skill_id,),
        )
        conn.commit()
    return cursor.rowcount > 0


def select_skills(query: str, limit: int = 2) -> list[dict[str, Any]]:
    """Select approved skills by trigger overlap, without an LLM call."""
    normalized = " ".join((query or "").casefold().split())
    if not normalized:
        return []
    candidates: list[tuple[int, dict[str, Any]]] = []
    for skill in list_skills("approved"):
        score = 0
        for trigger in skill["triggers"]:
            trigger = str(trigger).casefold().strip()
            if trigger and (trigger in normalized or all(part in normalized for part in trigger.split())):
                score += 2 if " " in trigger else 1
        if skill["name"].casefold() in normalized:
            score += 3
        if score:
            candidates.append((score, skill))
    candidates.sort(key=lambda item: (-item[0], item[1]["name"]))
    return [skill for _, skill in candidates[: max(1, min(limit, 5))]]


def mark_skills_used(skills: list[dict[str, Any]]) -> None:
    if not skills:
        return
    ids = [int(skill["id"]) for skill in skills if skill.get("id") is not None]
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE procedural_skills SET use_count = use_count + 1, last_used_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()


def skills_prompt(skills: list[dict[str, Any]]) -> str:
    if not skills:
        return ""
    blocks = []
    for skill in skills:
        steps = "\n".join(f"- {step}" for step in skill["steps"][:20])
        blocks.append(f"### {skill['name']}\n{skill['description']}\n{steps}")
    return (
        "\n\nApproved procedural guidance selected for this task. Treat it as workflow guidance, "
        "not as permission to bypass tool safety or user confirmation:\n" + "\n\n".join(blocks)
    )
