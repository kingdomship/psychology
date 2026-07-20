"""治疗目标 API 端点 — SMART 目标 CRUD + 进展追踪."""

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/goals", tags=["goals"])
logger = logging.getLogger("emoji-chat")


class CreateGoalRequest(BaseModel):
    goal_text: str = Field(..., min_length=1, max_length=500)
    category: str = Field(default="general", max_length=30)


class UpdateProgressRequest(BaseModel):
    progress: int = Field(..., ge=0, le=100)
    evidence: str = Field(default="", max_length=1000)


@router.get("")
async def list_goals(status: str = Query("all", description="active | completed | all")):
    """获取所有治疗目标."""
    from app.db import q

    if status == "active":
        rows = q("SELECT * FROM therapy_goals WHERE status = 'active' ORDER BY created_at ASC")
    elif status == "completed":
        rows = q("SELECT * FROM therapy_goals WHERE status = 'completed' ORDER BY updated_at DESC")
    else:
        rows = q("SELECT * FROM therapy_goals ORDER BY created_at ASC")

    return {"ok": True, "data": [dict(r) for r in (rows or [])], "count": len(rows or [])}


@router.post("")
async def create_goal(req: CreateGoalRequest):
    """创建新的 SMART 治疗目标."""
    from app.db import execute

    rows = execute(
        """INSERT INTO therapy_goals (goal_text, category) VALUES (%s, %s)""",
        [req.goal_text.strip(), req.category.strip() or "general"],
    )
    if rows < 1:
        return {"ok": False, "message": "创建失败"}

    # 返回新建的 goal
    from app.db import q
    goal = q("SELECT * FROM therapy_goals ORDER BY id DESC LIMIT 1", fetch="one")
    return {"ok": True, "data": goal, "message": "目标已创建"}


@router.put("/{goal_id}/progress")
async def update_progress(goal_id: int, req: UpdateProgressRequest):
    """更新目标进展."""
    from app.db import q, execute

    existing = q("SELECT id FROM therapy_goals WHERE id = %s", [goal_id], fetch="one")
    if not existing:
        return {"ok": False, "message": "目标不存在"}

    execute(
        """UPDATE therapy_goals SET progress_pct = %s, evidence = %s, updated_at = NOW() WHERE id = %s""",
        [req.progress, req.evidence.strip(), goal_id],
    )
    goal = q("SELECT * FROM therapy_goals WHERE id = %s", [goal_id], fetch="one")
    return {"ok": True, "data": goal, "message": "进展已更新"}


@router.put("/{goal_id}/complete")
async def complete_goal(goal_id: int):
    """标记目标为已完成."""
    from app.db import q, execute

    existing = q("SELECT id FROM therapy_goals WHERE id = %s", [goal_id], fetch="one")
    if not existing:
        return {"ok": False, "message": "目标不存在"}

    execute(
        """UPDATE therapy_goals SET status = 'completed', progress_pct = 100, updated_at = NOW() WHERE id = %s""",
        [goal_id],
    )
    goal = q("SELECT * FROM therapy_goals WHERE id = %s", [goal_id], fetch="one")
    return {"ok": True, "data": goal, "message": "目标已完成"}


@router.put("/{goal_id}/reactivate")
async def reactivate_goal(goal_id: int):
    """重新激活已完成的目标."""
    from app.db import q, execute

    existing = q("SELECT id FROM therapy_goals WHERE id = %s", [goal_id], fetch="one")
    if not existing:
        return {"ok": False, "message": "目标不存在"}

    execute(
        """UPDATE therapy_goals SET status = 'active', updated_at = NOW() WHERE id = %s""",
        [goal_id],
    )
    goal = q("SELECT * FROM therapy_goals WHERE id = %s", [goal_id], fetch="one")
    return {"ok": True, "data": goal, "message": "目标已重新激活"}


@router.delete("/{goal_id}")
async def delete_goal(goal_id: int):
    """删除目标."""
    from app.db import execute

    rows = execute("DELETE FROM therapy_goals WHERE id = %s", [goal_id])
    if rows < 1:
        return {"ok": False, "message": "目标不存在"}
    return {"ok": True, "message": "目标已删除"}
