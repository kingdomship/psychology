"""Life domain tracking — structured awareness of what the user cares about.

Tracks 6 life domains with status (positive/negative/neutral) and salience.
Uses a hybrid approach: keyword-based domain detection + Panksepp affect scores
for status inference. Zero extra LLM calls — reuses existing affect data.
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone

from app.config import LIFE_DOMAINS_PATH, archive_lock

logger = logging.getLogger("emoji-chat")

# ── Domain definitions ─────────────────────────────────────────────────────

DOMAINS = {
    "work": {
        "label": "工作",
        "keywords": [
            "工作", "上班", "加班", "老板", "领导", "同事", "职场", "项目",
            "开会", "汇报", "跳槽", "面试", "辞职", "裁员", "薪资", "工资",
            "任务", "ddl", "deadline", "甲方", "乙方", "客户", "出差",
        ]
    },
    "relationships": {
        "label": "关系",
        "keywords": [
            "朋友", "对象", "女朋友", "男朋友", "恋人", "伴侣", "家人", "父母",
            "妈妈", "爸爸", "孩子", "老公", "老婆", "闺蜜", "兄弟", "分手",
            "吵架", "冷战", "相亲", "约会", "暧昧", "表白", "暗恋", "前任",
        ]
    },
    "health": {
        "label": "健康",
        "keywords": [
            "身体", "健康", "生病", "医院", "失眠", "焦虑", "抑郁", "运动",
            "健身", "跑步", "瑜伽", "减肥", "饮食", "熬夜", "头疼", "累",
            "疲劳", "体检", "心理", "emo", "压力", "崩溃",
        ]
    },
    "hobbies": {
        "label": "兴趣",
        "keywords": [
            "喜欢", "爱好", "游戏", "电影", "音乐", "书", "摄影", "画画",
            "旅行", "旅游", "美食", "做菜", "猫", "狗", "宠物", "动漫",
            "追剧", "综艺", "b站", "番", "小说", "写作", "编程", "代码",
        ]
    },
    "finance": {
        "label": "财务",
        "keywords": [
            "钱", "工资", "理财", "买房", "租房", "贷款", "花销", "省钱",
            "投资", "股票", "基金", "副业", "赚钱", "贵", "便宜", "消费",
        ]
    },
    "growth": {
        "label": "成长",
        "keywords": [
            "学习", "考试", "考证", "考研", "读书", "技能", "进步", "改变",
            "方向", "迷茫", "意义", "目标", "计划", "未来", "梦想", "努力",
            "坚持", "自律", "拖延", "效率", "提升", "课程", "教程", "学",
        ]
    },
}

# Affect dimension → status mapping
# High SEEKING + PLAY → positive; high FEAR/PANIC/RAGE → negative
_POSITIVE_AFFECT = {"seeking", "play", "care"}
_NEGATIVE_AFFECT = {"fear", "rage", "panic"}

_lock = threading.Lock()


# ── Persistence ─────────────────────────────────────────────────────────────

def _load() -> dict:
    if os.path.exists(LIFE_DOMAINS_PATH):
        try:
            with open(LIFE_DOMAINS_PATH) as f:
                return json.load(f)
        except Exception:
            logger.warning("Failed to load life domains", exc_info=True)
    return {
        key: {"status": "neutral", "salience": 0.0, "last_mention": ""}
        for key in DOMAINS
    }


def _save(data: dict):
    try:
        from app.config import atomic_write
        atomic_write(LIFE_DOMAINS_PATH, json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        logger.warning("Failed to save life domains", exc_info=True)


# ── Detection ───────────────────────────────────────────────────────────────

def detect_domain(msg: str) -> tuple[list[str], dict[str, float]]:
    """Return (matched_domains, {domain: keyword_count}) for a user message."""
    matched = []
    counts = {}
    for key, dom in DOMAINS.items():
        cnt = sum(1 for kw in dom["keywords"] if kw in msg)
        if cnt > 0:
            matched.append(key)
            counts[key] = cnt
    return matched, counts


def infer_status(msg: str, affect: dict | None = None) -> str:
    """Infer domain status from affect dimensions and sentiment cues.

    Uses existing Panksepp affect scores as the primary signal.
    Falls back to simple negation-word heuristics if affect is unavailable.
    """
    if affect:
        pos = sum(affect.get(dim, 0) for dim in _POSITIVE_AFFECT)
        neg = sum(affect.get(dim, 0) for dim in _NEGATIVE_AFFECT)
        if pos - neg > 0.1:
            return "positive"
        elif neg - pos > 0.1:
            return "negative"
        return "neutral"

    # Fallback: simple negation detection
    neg_words = ["烦", "累", "难", "讨厌", "无语", "崩溃", "压力", "焦虑", "不开心"]
    pos_words = ["开心", "喜欢", "期待", "有意思", "好玩", "棒", "不错", "哈哈"]
    neg_cnt = sum(1 for w in neg_words if w in msg)
    pos_cnt = sum(1 for w in pos_words if w in msg)
    if pos_cnt > neg_cnt:
        return "positive"
    elif neg_cnt > pos_cnt:
        return "negative"
    return "neutral"


# ── Update (called from _post_reply_pipeline) ───────────────────────────────

def update_life_domains(msg: str, affect: dict | None = None):
    """Update life domain state based on a single user message.

    Lightweight — keyword matching + affect inference, no LLM call.
    Designed to run every turn in the background pipeline.
    """
    matched, counts = detect_domain(msg)
    if not matched:
        return

    with _lock:
        data = _load()
        now = datetime.now(timezone.utc).isoformat()
        for domain in matched:
            entry = data.get(domain, {"status": "neutral", "salience": 0.0, "last_mention": ""})
            # EMA-smooth salience (alpha=0.1, stronger because keyword hits are already filtered)
            hit = min(counts[domain] / 3.0, 1.0)
            entry["salience"] = round(entry["salience"] * 0.9 + hit * 0.1, 3)
            # Infer status from affect (updates immediately, not smoothed)
            entry["status"] = infer_status(msg, affect)
            # Last mention snapshot
            entry["last_mention"] = msg[:200]
            data[domain] = entry
        _save(data)


# ── Context injection ───────────────────────────────────────────────────────

def get_life_domain_context() -> str:
    """Generate natural-language context string for system prompt injection.

    Returns empty string if no domains have salience > 0.05.
    Only includes domains the user has recently talked about.
    """
    data = _load()
    active = [
        (key, dom, data[key])
        for key, dom in DOMAINS.items()
        if data.get(key, {}).get("salience", 0) > 0.05
    ]
    if not active:
        return ""

    # Sort by salience, top 3 most salient
    active.sort(key=lambda x: x[2]["salience"], reverse=True)
    active = active[:3]

    lines = ["## 用户近况（仅供参考，不要每轮都提）"]
    for key, dom, entry in active:
        status_emoji = {"positive": "👍", "negative": "😔", "neutral": "💬"}.get(entry["status"], "")
        status_text = {"positive": "顺利", "negative": "有困扰", "neutral": "在关注"}.get(entry["status"], "")
        lines.append(f"- {dom['label']}：{status_text} {status_emoji}")

    # Guidance strength depends on how much info we have
    if len(active) <= 2:
        lines.append("（你目前对用户了解不多，上面这些偶尔提到就行，不要每轮都拿出来说。多聊新的，少翻旧账。）")
    else:
        lines.append("（你心里有数就好，挑相关的自然带过，不要逐条复述。）")
    return "\n".join(lines)


# ── 场景练习建议 ────────────────────────────────────────────────────────

# 轻量级引用 (避免从 simulator 循环导入)
_SCENARIO_REF = {
    "express_feelings": {"label": "表达感受", "icon": "💬", "example": "对某个人说出内心的感受"},
    "set_boundaries": {"label": "设立边界", "icon": "🛡️", "example": "对越界行为说"不""},
    "resolve_conflict": {"label": "冲突化解", "icon": "🤝", "example": "与有矛盾的人沟通"},
    "seek_support": {"label": "寻求支持", "icon": "🤲", "example": "向人开口寻求帮助"},
}

# 领域 → 场景类型映射 (哪些场景适合练习该领域的问题)
_DOMAIN_SCENARIO_MAP = {
    "work": ["set_boundaries", "seek_support", "resolve_conflict"],
    "relationships": ["express_feelings", "resolve_conflict", "set_boundaries"],
    "health": ["seek_support", "express_feelings"],
    "hobbies": ["express_feelings", "seek_support"],
    "finance": ["seek_support", "set_boundaries"],
    "growth": ["seek_support", "express_feelings"],
}

# 状态权重 (负面领域优先级最高)
_STATUS_WEIGHT = {"negative": 3, "neutral": 1, "positive": 0}

# 推荐理由
_REASONS = {
    "work": "你最近在工作中遇到了一些挑战，练习沟通技巧可能帮助你更好地应对",
    "relationships": "你在人际关系方面有些困扰，练习表达和沟通可能有助于改善",
    "health": "你最近状态不太好，学会向身边的人寻求支持也是很重要的能力",
    "hobbies": "你的兴趣爱好也可以成为练习真实表达的场景",
    "finance": "财务问题往往伴随着沟通压力，练习如何开口谈论钱的话题很有帮助",
    "growth": "你在关注个人成长，而沟通能力是成长的重要部分",
}


def get_scenario_suggestions() -> list[dict]:
    """基于用户生活领域状态，生成场景练习建议.

    读取 life_domains.json，找到状态负面或显著性高的领域，
    映射到相关场景类型，返回最多3个建议。

    返回: [{scenario_type, label, icon, example, domain, domain_label, reason, confidence}]
    """
    data = _load()
    suggestions = []
    seen_types: set[str] = set()

    # 给每个领域打分: 状态权重 * (1 + 显著性)
    scored = []
    for key, dom_def in DOMAINS.items():
        entry = data.get(key, {"status": "neutral", "salience": 0.0})
        weight = _STATUS_WEIGHT.get(entry.get("status", "neutral"), 0)
        salience = float(entry.get("salience", 0.0))
        score = weight * (1.0 + salience)
        if score > 0:
            scored.append((key, score, entry))

    scored.sort(key=lambda x: x[1], reverse=True)

    for domain, score, entry in scored:
        if len(suggestions) >= 3:
            break

        candidate_types = _DOMAIN_SCENARIO_MAP.get(domain, [])
        for st in candidate_types:
            if st in seen_types:
                continue
            ref = _SCENARIO_REF.get(st)
            if not ref:
                continue

            confidence = min(round(score / 3.0, 2), 0.95)
            suggestions.append({
                "scenario_type": st,
                "label": ref["label"],
                "icon": ref["icon"],
                "example": ref["example"],
                "domain": domain,
                "domain_label": DOMAINS[domain]["label"],
                "reason": _REASONS.get(domain, "这个场景可能值得练习"),
                "confidence": confidence,
            })
            seen_types.add(st)

    return suggestions
