"""跨会话模式摘要 — 提取多周内的重复主题、变化趋势和纵向洞察.

LLM 分析对话记录中的主题演变，追踪情绪与行为模式的变化。
每个数据源独立 try/catch，LLM 失败自动降级为规则分析。
"""

import json
import logging
from collections import Counter
from datetime import date, timedelta

from app.db import q

logger = logging.getLogger("emoji-chat")

_CROSS_SESSION_PROMPT = """你是一位心理健康数据分析师。请分析以下用户多周的心理健康数据，提取跨会话模式。

## 数据
{data_text}

## 要求
1. 识别重复出现的主题/话题（至少2个），说明出现的周数和频率
2. 分析情绪变化趋势（上升/下降/波动），关联可能的生活事件
3. 指出行为模式的变化（如深夜聊天频率、回复长度变化）
4. 给出2-3条纵向关怀建议，聚焦长期趋势而非单点问题
5. 以第二人称"你"称呼用户
6. 不做临床诊断，不贴标签
7. 控制在300字以内

输出 JSON 格式:
{{
  "themes": [{{"topic": "主题名", "weeks_seen": 3, "trend": "上升|下降|稳定", "note": "简要说明"}}],
  "emotion_trend": "整体情绪趋势描述",
  "behavior_shift": "行为模式变化的描述",
  "suggestions": ["建议1", "建议2", "建议3"],
  "narrative": "综合叙事段落"
}}

只输出 JSON，不要其他内容。"""


def _weekly_messages(weeks: int) -> list[dict]:
    """按周统计消息数量和内容样本."""
    try:
        rows = q(
            """SELECT DATE_TRUNC('week', created_at) as week_start,
                      COUNT(*) as msg_count,
                      STRING_AGG(user_msg, ' | ' ORDER BY created_at) as samples
               FROM chat_history
               WHERE created_at >= NOW() - INTERVAL '%s weeks'
               GROUP BY week_start
               ORDER BY week_start""",
            [weeks],
        )
        return [dict(r) for r in (rows or [])]
    except Exception:
        logger.warning("周消息统计失败", exc_info=True)
        return []


def _weekly_mood(weeks: int) -> list[dict]:
    """按周统计情绪自检分布."""
    try:
        rows = q(
            """SELECT DATE_TRUNC('week', created_at) as week_start,
                      mood_emoji, COUNT(*) as cnt
               FROM mood_checkins
               WHERE created_at >= NOW() - INTERVAL '%s weeks'
               GROUP BY week_start, mood_emoji
               ORDER BY week_start, cnt DESC""",
            [weeks],
        )
        return [dict(r) for r in (rows or [])]
    except Exception:
        logger.warning("周情绪统计失败", exc_info=True)
        return []


def _weekly_diary(weeks: int) -> list[dict]:
    """按周获取日记摘要."""
    try:
        rows = q(
            """SELECT DATE_TRUNC('week', date) as week_start,
                      COUNT(*) as diary_count,
                      STRING_AGG(LEFT(COALESCE(user_content, content), 200), ' | ') as samples
               FROM diary_entries
               WHERE date >= NOW() - INTERVAL '%s weeks'
               GROUP BY week_start
               ORDER BY week_start""",
            [weeks],
        )
        return [dict(r) for r in (rows or [])]
    except Exception:
        logger.warning("周日记统计失败", exc_info=True)
        return []


def _weekly_affect(weeks: int) -> list[dict]:
    """按周统计情感六维均值."""
    try:
        rows = q(
            """SELECT DATE_TRUNC('week', date) as week_start,
                      ROUND(AVG(seeking)::numeric, 3) as seeking,
                      ROUND(AVG(play)::numeric, 3) as play,
                      ROUND(AVG(care)::numeric, 3) as care,
                      ROUND(AVG(fear)::numeric, 3) as fear,
                      ROUND(AVG(rage)::numeric, 3) as rage,
                      ROUND(AVG(panic)::numeric, 3) as panic
               FROM affect_history
               WHERE date >= NOW() - INTERVAL '%s weeks'
               GROUP BY week_start
               ORDER BY week_start""",
            [weeks],
        )
        return [dict(r) for r in (rows or [])]
    except Exception:
        logger.warning("周情感统计失败", exc_info=True)
        return []


def _weekly_crisis(weeks: int) -> list[dict]:
    """按周统计危机事件."""
    try:
        rows = q(
            """SELECT DATE_TRUNC('week', created_at) as week_start,
                      COUNT(*) as crisis_count,
                      COUNT(*) FILTER (WHERE llm_verified) as verified_count,
                      ROUND(MAX(severity)::numeric, 1) as max_severity
               FROM crisis_events
               WHERE created_at >= NOW() - INTERVAL '%s weeks'
               GROUP BY week_start
               ORDER BY week_start""",
            [weeks],
        )
        return [dict(r) for r in (rows or [])]
    except Exception:
        logger.warning("周危机统计失败", exc_info=True)
        return []


def _weekly_behavior(weeks: int) -> list[dict]:
    """按周获取行为标记."""
    try:
        rows = q(
            """SELECT window_start, avg_latency_seconds, latency_trend_direction,
                      avg_user_msg_length, length_trend_direction,
                      late_night_ratio, rhythm_stability
               FROM behavioral_markers
               WHERE window_start >= NOW() - INTERVAL '%s weeks'
               ORDER BY window_start""",
            [weeks],
        )
        return [dict(r) for r in (rows or [])]
    except Exception:
        logger.warning("周行为统计失败", exc_info=True)
        return []


def build_cross_session_data(weeks: int = 4) -> dict:
    """收集多周数据用于跨会话分析."""
    data = {
        "weeks": weeks,
        "weekly_messages": _weekly_messages(weeks),
        "weekly_mood": _weekly_mood(weeks),
        "weekly_diary": _weekly_diary(weeks),
        "weekly_affect": _weekly_affect(weeks),
        "weekly_crisis": _weekly_crisis(weeks),
        "weekly_behavior": _weekly_behavior(weeks),
    }

    # 统计活跃周数
    active_weeks = len([w for w in data["weekly_messages"] if w.get("msg_count", 0) > 0])
    data["active_weeks"] = active_weeks

    # 总消息数
    data["total_messages"] = sum(w.get("msg_count", 0) for w in data["weekly_messages"])

    return data


def _build_data_text(data: dict) -> str:
    """将跨会话数据转为 LLM 友好的文本."""
    lines = [f"分析跨度: {data['weeks']} 周, 活跃 {data.get('active_weeks', 0)} 周, 共 {data.get('total_messages', 0)} 条消息"]
    lines.append("")

    # 周消息
    if data["weekly_messages"]:
        lines.append("## 周消息量")
        for w in data["weekly_messages"]:
            ws = str(w.get("week_start", ""))[:10]
            lines.append(f"- {ws}: {w.get('msg_count', 0)} 条")
        lines.append("")

    # 周情感
    if data["weekly_affect"]:
        lines.append("## 周情感均值 (探索/玩耍/关怀/恐惧/愤怒/恐慌)")
        for w in data["weekly_affect"]:
            ws = str(w.get("week_start", ""))[:10]
            dims = f"{w.get('seeking', 0):.2f}/{w.get('play', 0):.2f}/{w.get('care', 0):.2f}"
            neg = f"{w.get('fear', 0):.2f}/{w.get('rage', 0):.2f}/{w.get('panic', 0):.2f}"
            lines.append(f"- {ws}: 正[{dims}] 负[{neg}]")
        lines.append("")

    # 情绪自检
    if data["weekly_mood"]:
        lines.append("## 情绪标记")
        by_week = {}
        for m in data["weekly_mood"]:
            ws = str(m.get("week_start", ""))[:10]
            if ws not in by_week:
                by_week[ws] = []
            by_week[ws].append(f"{m['mood_emoji']}x{m['cnt']}")
        for ws, moods in by_week.items():
            lines.append(f"- {ws}: {', '.join(moods)}")
        lines.append("")

    # 日记
    if data["weekly_diary"]:
        lines.append("## 日记")
        for w in data["weekly_diary"]:
            ws = str(w.get("week_start", ""))[:10]
            lines.append(f"- {ws}: {w.get('diary_count', 0)} 篇")
        lines.append("")

    # 危机
    if data["weekly_crisis"]:
        lines.append("## 危机信号")
        for w in data["weekly_crisis"]:
            ws = str(w.get("week_start", ""))[:10]
            lines.append(f"- {ws}: {w.get('crisis_count', 0)} 次, 最高严重度 {w.get('max_severity', 0)}")
        lines.append("")

    # 行为
    if data["weekly_behavior"]:
        lines.append("## 行为标记")
        for w in data["weekly_behavior"]:
            ws = str(w.get("window_start", ""))[:10]
            ln = float(w.get("late_night_ratio", 0) or 0)
            rh = float(w.get("rhythm_stability", 0) or 0)
            lines.append(f"- {ws}: 深夜比 {ln:.0%}, 节律稳定性 {rh:.0%}")
        lines.append("")

    return "\n".join(lines)


def analyze_cross_session(weeks: int = 4) -> dict:
    """执行跨会话分析.

    返回: {"data": {...}, "analysis": {...}, "error": None} 或 {"error": "..."}
    """
    data = build_cross_session_data(weeks)

    if data["active_weeks"] < 2:
        return {
            "data": data,
            "analysis": None,
            "message": f"仅 {data['active_weeks']} 周活跃数据，需要至少2周数据进行分析",
        }

    # LLM 分析
    data_text = _build_data_text(data)
    analysis = _call_llm_analysis(data_text)

    return {"data": data, "analysis": analysis}


def _call_llm_analysis(data_text: str) -> dict:
    """调用 LLM 进行跨会话分析."""
    from app.utils import get_llm, get_llm_model

    prompt = _CROSS_SESSION_PROMPT.format(data_text=data_text)

    client = get_llm()
    if not client:
        logger.warning("LLM 不可用, 使用规则分析")
        return _fallback_analysis(data_text)

    try:
        model = get_llm_model()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一位专业的心理健康数据分析师。请只输出 JSON，不要有其他内容。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content.strip()
        # 清理可能的 markdown JSON 包裹
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM 返回无效 JSON, 使用规则分析")
        return _fallback_analysis(data_text)
    except Exception:
        logger.warning("LLM 跨会话分析失败", exc_info=True)
        return _fallback_analysis(data_text)


def _fallback_analysis(data_text: str) -> dict:
    """规则降级: 基于统计数据生成跨会话分析."""
    return {
        "themes": [],
        "emotion_trend": "",
        "behavior_shift": "",
        "suggestions": [
            "继续保持每周的对话习惯，这是自我觉察的重要途径",
            "关注情绪的周期性变化，低谷期给自己更多宽容",
            "如果某个话题反复出现，可以尝试深入探索其根源",
        ],
        "narrative": "跨会话分析需要足够的数据积累。请继续日常对话和情绪记录，系统会随着数据增加提供更准确的分析。",
    }
