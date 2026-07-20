"""分析报告 API 端点."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Query

from services.report.aggregator import (
    get_latest_report,
    list_reports,
    get_report_by_id,
    generate_report,
)

router = APIRouter(prefix="/api/report", tags=["report"])
logger = logging.getLogger("emoji-chat")


@router.get("/latest")
async def latest():
    """返回最新一份报告 (首页默认展示)."""
    report = get_latest_report()
    if not report:
        return {"ok": True, "data": None, "message": "暂无报告，活跃天数达到7天后将自动生成"}
    return {"ok": True, "data": report}


@router.get("/list")
async def list(limit: int = Query(20, ge=1, le=100)):
    """返回报告历史列表 (精简字段)."""
    reports = list_reports(limit)
    return {"ok": True, "data": reports, "count": len(reports)}


@router.get("/cross-session")
async def cross_session(weeks: int = Query(4, ge=2, le=12, description="分析跨度(周)")):
    """跨会话模式摘要 — LLM 提取重复主题 + 变化趋势 + 纵向洞察."""
    from services.report.cross_session import analyze_cross_session
    result = analyze_cross_session(weeks)
    return {"ok": True, **result}


@router.get("/{report_id}")
async def get(report_id: int):
    """返回指定报告的完整数据."""
    report = get_report_by_id(report_id)
    if not report:
        return {"ok": False, "message": "报告不存在"}
    return {"ok": True, "data": report}


@router.post("/generate")
async def generate(days: int = Query(7, ge=7, le=90, description="报告覆盖天数")):
    """手动生成指定天数的报告."""
    if days not in (7, 14, 30, 60, 90):
        return {"ok": False, "message": "支持的天数: 7, 14, 30, 60, 90"}

    date_to = date.today()
    date_from = date_to - timedelta(days=days)

    rid = generate_report(
        date_from=date_from,
        date_to=date_to,
        report_type="manual",
        milestone_label=None,
    )

    if rid is None:
        return {"ok": False, "message": "报告生成失败"}

    report = get_report_by_id(rid)
    return {"ok": True, "data": report, "message": f"{days}天报告已生成"}
