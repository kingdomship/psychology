"""场景练习 API 端点 — AI 扮演不同角色，用户练习真实人际对话."""

import logging

from fastapi import APIRouter, Query

from services.training.simulator import (
    SCENARIO_TYPES,
    create_session,
    generate_random_scenario,
    get_session,
    end_session,
)

router = APIRouter(prefix="/api/training", tags=["training"])
logger = logging.getLogger("emoji-chat")


@router.get("/clients")
async def list_scenarios():
    """列出所有可用的场景类型."""
    types = [
        {
            "id": k,
            "label": v["label"],
            "icon": v["icon"],
            "example": v["example"],
            "description": v["description"],
        }
        for k, v in SCENARIO_TYPES.items()
    ]
    return {"ok": True, "data": types}


@router.post("/suggest")
async def suggest():
    """基于用户的生活领域状态，AI 推荐场景练习."""
    try:
        from services.psych.life_domains import get_scenario_suggestions
        suggestions = get_scenario_suggestions()
        return {"ok": True, "data": suggestions}
    except Exception:
        logger.warning("场景建议生成失败", exc_info=True)
        return {"ok": True, "data": []}


@router.post("/start")
async def start(
    scenario_type: str = Query("express_feelings", description="场景类型"),
    situation: str = Query("", description="自定义场景描述"),
    ai_role: str = Query("", description="AI 扮演的角色名称"),
):
    """开始新的场景练习会话."""
    result = create_session(scenario_type, situation.strip(), ai_role.strip())
    if "error" in result:
        return {"ok": False, **result}
    return {"ok": True, **result}


@router.post("/end")
async def end(session_id: str = Query(...)):
    """结束练习并生成反馈."""
    result = end_session(session_id)
    if "error" in result:
        return {"ok": False, **result}
    return {"ok": True, **result}


@router.get("/status")
async def status(session_id: str = Query(...)):
    """获取练习会话状态."""
    session = get_session(session_id)
    if not session:
        return {"ok": False, "error": "会话不存在"}
    return {
        "ok": True,
        "session_id": session["id"],
        "scenario_type": session["scenario_type"],
        "scenario_label": session["scenario_label"],
        "scenario_icon": session["scenario_icon"],
        "ai_role": session["ai_role"],
        "status": session["status"],
        "turn_count": len([t for t in session["turns"] if t["role"] == "ai"]),
    }


@router.post("/random")
async def random_scenario():
    """LLM 随机生成一个场景练习."""
    result = generate_random_scenario()
    if "error" in result:
        return {"ok": False, **result}
    return {"ok": True, **result}
