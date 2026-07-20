"""会话导出 API — 逐字稿 Markdown / JSON 下载."""

import logging
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.db import q

router = APIRouter(prefix="/api/export", tags=["export"])
logger = logging.getLogger("emoji-chat")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/transcript")
async def export_transcript(
    date_from: str = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: str = Query(None, description="结束日期 YYYY-MM-DD"),
    fmt: str = Query("md", description="输出格式: md | json"),
):
    """导出指定日期范围内的对话逐字稿."""
    # Validate date format to prevent CRLF injection
    if date_from and not _DATE_RE.match(date_from):
        return {"ok": False, "message": "date_from 格式无效，应为 YYYY-MM-DD"}
    if date_to and not _DATE_RE.match(date_to):
        return {"ok": False, "message": "date_to 格式无效，应为 YYYY-MM-DD"}

    conditions = []
    params = []

    if date_from:
        conditions.append("created_at >= %s")
        params.append(date_from)
    else:
        conditions.append("created_at >= (NOW() - INTERVAL '7 days')")

    if date_to:
        conditions.append("created_at <= %s")
        params.append(date_to + " 23:59:59")

    where = " AND ".join(conditions)
    rows = q(
        f"SELECT user_msg, avatar_reply, emotion_label, created_at FROM chat_history WHERE {where} ORDER BY id ASC",
        params,
    )

    if not rows:
        return {"ok": True, "data": "", "count": 0, "message": "所选日期范围内无对话记录"}

    if fmt == "json":
        data = []
        for r in rows:
            ts = r["created_at"]
            data.append({
                "time": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "user": r["user_msg"],
                "avatar": r["avatar_reply"],
                "emotion": r["emotion_label"] or "",
            })
        return {"ok": True, "format": "json", "count": len(data), "data": data}

    # Markdown format
    lines = ["# 对话逐字稿", ""]
    if date_from and date_to:
        lines.append(f"**期间**: {date_from} ~ {date_to}")
    elif date_from:
        lines.append(f"**起始**: {date_from}")
    lines.append(f"**对话轮数**: {len(rows)}")
    lines.append(f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    for r in rows:
        ts = r["created_at"]
        time_str = ts.strftime("%m-%d %H:%M") if isinstance(ts, datetime) else str(ts)[:16]
        emotion = r["emotion_label"] or ""
        lines.append(f"### {time_str}")
        lines.append("")
        lines.append(f"**用户**: {r['user_msg']}")
        lines.append("")
        emoji_line = f"**AI** ({emotion}): {r['avatar_reply']}" if emotion else f"**AI**: {r['avatar_reply']}"
        lines.append(emoji_line)
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    safe_name = (date_from or "recent").replace("\r", "").replace("\n", "")
    return PlainTextResponse(content, media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f"attachment; filename=transcript-{safe_name}.md"})
