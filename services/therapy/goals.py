"""治疗目标追踪 — SMART 目标 CRUD + 上下文注入."""

import logging

logger = logging.getLogger("emoji-chat")


def get_active_goals() -> list[dict]:
    """获取所有活跃的治疗目标."""
    from app.db import q
    rows = q(
        """SELECT * FROM therapy_goals WHERE status = 'active' ORDER BY created_at ASC"""
    )
    return [dict(r) for r in (rows or [])]


def get_goal_context() -> str | None:
    """生成目标上下文 (供 cognitive bus 注入)."""
    goals = get_active_goals()
    if not goals:
        return None
    items = []
    for g in goals:
        pct = g.get("progress_pct", 0)
        bar = "".join(["▓" if i < pct // 10 else "░" for i in range(10)])
        items.append(f"- [{bar}] {pct}% {g['goal_text']}")
    return "## 当前治疗目标\n" + "\n".join(items) + "\n请在合适的时候帮助用户推进这些目标，但不要强行提及或生硬插入对话。"


def update_goal_progress(goal_id: int, progress: int, evidence: str = "") -> bool:
    """更新目标进展."""
    from app.db import execute
    execute(
        """UPDATE therapy_goals SET progress_pct = %s, evidence = %s, updated_at = NOW() WHERE id = %s""",
        [min(100, max(0, progress)), evidence, goal_id],
    )
    return True
