"""临床评估 API — PHQ-9 / GAD-7 对话式量表."""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.db import q, execute
from services.assessment.scales import SCALES

router = APIRouter(prefix="/api/assessment", tags=["assessment"])
logger = logging.getLogger("emoji-chat")


@router.get("/scales")
async def list_scales():
    """列出可用的评估量表."""
    items = []
    for key, scale in SCALES.items():
        items.append({
            "id": key,
            "name": scale["name"],
            "total_questions": scale["total_questions"],
        })
    return {"ok": True, "data": items}


@router.post("/start")
async def start(scale_id: str = Query("phq9", description="量表ID: phq9 | gad7")):
    """开始一次评估, 返回第一个问题."""
    scale = SCALES.get(scale_id)
    if not scale:
        return {"ok": False, "message": "无效量表ID，支持: phq9, gad7"}

    # 创建评估会话
    row = q(
        """INSERT INTO assessment_sessions (scale_id, status, current_question, answers)
           VALUES (%s, 'in_progress', 1, '[]')
           RETURNING id""",
        [scale_id],
        fetch="one",
    )
    session_id = row["id"]

    q1 = scale["questions"][0]
    return {
        "ok": True,
        "session_id": session_id,
        "scale": scale["name"],
        "question_index": 1,
        "total_questions": scale["total_questions"],
        "question": q1["text"],
        "options": scale["options"],
        "domain": q1["domain"],
    }


@router.post("/answer")
async def answer(session_id: int = Query(...), score: int = Query(..., ge=0, le=3)):
    """提交当前问题的答案, 返回下一题或结果."""
    session = q(
        "SELECT * FROM assessment_sessions WHERE id = %s AND status = 'in_progress'",
        [session_id],
        fetch="one",
    )
    if not session:
        return {"ok": False, "message": "评估会话不存在或已完成"}

    scale_id = session["scale_id"]
    scale = SCALES.get(scale_id)
    if not scale:
        return {"ok": False, "message": "量表配置丢失"}

    # 追加答案
    answers = json.loads(session["answers"] or "[]")
    q_idx = session["current_question"]
    q_text = scale["questions"][q_idx - 1]["text"]
    answers.append({"q": q_idx, "text": q_text, "score": score})

    # 是否已完成?
    if q_idx >= scale["total_questions"]:
        total_score = sum(a["score"] for a in answers)
        result = scale["interpret"](total_score)
        execute(
            "UPDATE assessment_sessions SET answers=%s, total_score=%s, status='completed', completed_at=NOW() WHERE id=%s",
            [json.dumps(answers, ensure_ascii=False), total_score, session_id],
        )
        return {
            "ok": True,
            "session_id": session_id,
            "completed": True,
            "total_score": total_score,
            "max_score": result["max_score"],
            "level": result["level"],
            "suggestion": result["suggestion"],
            "answers": answers,
        }

    # 下一题
    next_idx = q_idx + 1
    execute(
        "UPDATE assessment_sessions SET current_question=%s, answers=%s WHERE id=%s",
        [next_idx, json.dumps(answers, ensure_ascii=False), session_id],
    )
    next_q = scale["questions"][next_idx - 1]
    return {
        "ok": True,
        "session_id": session_id,
        "completed": False,
        "question_index": next_idx,
        "total_questions": scale["total_questions"],
        "question": next_q["text"],
        "options": scale["options"],
        "domain": next_q["domain"],
    }


@router.get("/result")
async def result(session_id: int = Query(...)):
    """获取已完成评估的结果."""
    session = q(
        "SELECT * FROM assessment_sessions WHERE id = %s",
        [session_id],
        fetch="one",
    )
    if not session:
        return {"ok": False, "message": "会话不存在"}

    answers = json.loads(session["answers"] or "[]")
    scale = SCALES.get(session["scale_id"])
    total_score = session["total_score"] or 0
    result = scale["interpret"](total_score) if scale else {}

    return {
        "ok": True,
        "data": {
            "session_id": session["id"],
            "scale": scale["name"] if scale else "",
            "status": session["status"],
            "total_score": total_score,
            "level": result.get("level", ""),
            "suggestion": result.get("suggestion", ""),
            "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
            "answers": answers,
        },
    }


@router.get("/history")
async def history(limit: int = Query(10, ge=1, le=50)):
    """获取评估历史列表."""
    rows = q(
        """SELECT id, scale_id, status, total_score, completed_at
           FROM assessment_sessions
           WHERE status = 'completed'
           ORDER BY completed_at DESC LIMIT %s""",
        [limit],
    )
    result = []
    for r in (rows or []):
        d = dict(r)
        scale = SCALES.get(d["scale_id"])
        d["scale_name"] = scale["name"] if scale else ""
        if d.get("completed_at"):
            d["completed_at"] = d["completed_at"].isoformat()
        result.append(d)
    return {"ok": True, "data": result}
