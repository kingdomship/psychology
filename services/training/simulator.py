"""场景练习模拟器 — AI 扮演不同角色，让用户在安全环境中练习真实人际对话.

Session 状态机:
  IDLE → ACTIVE (开始练习) → FEEDBACK (结束练习, 生成反馈) → IDLE
"""

import json
import logging
import threading
import uuid

logger = logging.getLogger("emoji-chat")

# 场景类型定义 (prompt 模板, 支持 {ai_role} 和 {situation} 占位符)
SCENARIO_TYPES = {
    "express_feelings": {
        "label": "表达感受",
        "icon": "💬",
        "example": "对某个人说出你内心的真实感受",
        "description": "练习向重要的人表达你的情感——无论是爱、感激、失望还是伤心",
        "default_ai_role": "对方",
        "ai_role_prompt": """你正在扮演{ai_role}。{situation}

你的特点是:
- 你在{ai_role}这个角色中，有着自然的情感和反应
- 你不会读心，对方（用户）不表达你就不知道TA在想什么
- 当对方表达感受时，你会根据内容做出合理的情感反应（可能理解，也可能防御或回避）
- 你的反应取决于对方表达的方式——真诚的表达更容易获得你的理解
- 请以第一人称自然地回应，只说你会说的话

每次回复控制在40-120字。""",
    },
    "set_boundaries": {
        "label": "设立边界",
        "icon": "🛡️",
        "example": "对越界的行为说“不”",
        "description": "练习在被人越界时坚定地表达自己的界限——对不合理的请求、侵犯或消耗说“不”",
        "default_ai_role": "越界者",
        "ai_role_prompt": """你正在扮演{ai_role}。{situation}

你的特点是:
- 你在某个方面正在越界——你可能在提不合理的要求、占用对方的时间精力、或者忽视对方的感受
- 你不会轻易放弃，一开始会试图说服或施压
- 当对方坚定地表达边界时，你最终会退让，但过程可能有些曲折
- 你并非恶意，只是习惯性地以自己的需求为先
- 请以第一人称自然地回应

每次回复控制在40-120字。""",
    },
    "resolve_conflict": {
        "label": "冲突化解",
        "icon": "🤝",
        "example": "与有矛盾的人进行沟通",
        "description": "练习在冲突中保持冷静、表达自己、理解对方，找到共同的解决方向",
        "default_ai_role": "冲突对象",
        "ai_role_prompt": """你正在扮演{ai_role}。{situation}

你的特点是:
- 你和对方（用户）之间存在真实的矛盾或分歧
- 你也有自己的立场和理由，并不认为全是自己的错
- 刚开始你可能带有情绪（生气、委屈、冷漠），但并非不愿沟通
- 当对方展现出理解时，你也愿意缓和态度
- 如果对方攻击或指责，你会防御性回应甚至升级冲突
- 请以第一人称自然地回应

每次回复控制在40-120字。""",
    },
    "seek_support": {
        "label": "寻求支持",
        "icon": "🤲",
        "example": "向人开口寻求帮助",
        "description": "练习在需要的时候开口向他人寻求支持——情感上的或实际上的帮助",
        "default_ai_role": "支持对象",
        "ai_role_prompt": """你正在扮演{ai_role}。{situation}

你的特点是:
- 你愿意帮助对方（用户），但你也有自己的生活节奏和限制
- 你不知道对方具体经历了什么——需要TA主动告诉你
- 你关心对方，但不会读心，需要清晰的请求才能提供帮助
- 你的反应取决于对方求助的方式——直接坦诚的求助更容易得到积极响应
- 请以第一人称自然地回应

每次回复控制在40-120字。""",
    },
}

# 默认场景描述 (当用户不提供自定义 situation 时使用)
_DEFAULT_SITUATIONS = {
    "express_feelings": "你和对方之间有些话一直没说出口，今天你决定说出来。",
    "set_boundaries": "对方最近一直在占用你的时间和精力，让你感到疲惫。你决定和TA谈谈你的界限。",
    "resolve_conflict": "你们之间发生了一些不愉快的事情，关系有些紧张。你希望能够化解这个矛盾。",
    "seek_support": "你最近遇到了一些困难，需要找人聊聊或者寻求一些帮助。",
}

# 反馈 prompt (人际沟通能力评估)
_FEEDBACK_PROMPT = """你是一位人际沟通教练。请分析以下场景练习记录，为用户提供关于人际沟通能力的反馈。

## 场景类型
{scenario_label}

## 场景描述
{situation}

## AI 扮演的角色
{ai_role}

## 练习记录
{dialogue}

## 评估维度 (每个维度1-5分)
1. 表达清晰度: 是否清晰、准确地表达了自己的想法和感受，而不是含糊或绕弯子
2. 情绪觉察: 是否意识到并承认了自己的情绪状态（"我感到..."而非"你让我..."）
3. 边界维护: 是否保护了自己的界限，没有因为压力而违背自己的底线
4. 自信表达: 表达是否坚定而不退缩，同时也不攻击或指责对方
5. 换位思考: 是否考虑到了对方的立场和感受，展现出理解对方的意愿

## 要求
1. 给出每个维度的评分（整数1-5分）和简要说明（一句话即可）
2. 指出2-3个做得好的地方（具体引用对话）
3. 指出2-3个可以改进的地方（给出具体建议）
4. 给出一句总体建议和鼓励
5. 以中文输出，语气鼓励性而非评判性

输出 JSON 格式:
{{
  "scores": {{
    "clarity": 3,
    "awareness": 4,
    "boundary": 3,
    "assertiveness": 3,
    "perspective": 4
  }},
  "highlights": ["亮点1", "亮点2"],
  "improvements": ["改进点1", "改进点2"],
  "overall": "总体建议一句话"
}}

只输出 JSON，不要其他内容。"""


# ── Session 管理 ──

_sessions: dict[str, dict] = {}  # session_id → state
_lock = threading.Lock()


def create_session(scenario_type: str, situation: str = "", ai_role: str = "") -> dict:
    """创建新的场景练习会话."""
    if scenario_type not in SCENARIO_TYPES:
        return {"error": f"未知场景类型: {scenario_type}", "valid_types": list(SCENARIO_TYPES.keys())}

    st = SCENARIO_TYPES[scenario_type]
    if not situation:
        situation = _DEFAULT_SITUATIONS.get(scenario_type, "")
    if not ai_role:
        ai_role = st["default_ai_role"]

    # 填充 prompt 模板
    prompt = st["ai_role_prompt"].format(ai_role=ai_role, situation=situation)

    session_id = uuid.uuid4().hex[:12]
    session = {
        "id": session_id,
        "scenario_type": scenario_type,
        "scenario_label": st["label"],
        "scenario_icon": st["icon"],
        "ai_role": ai_role,
        "situation": situation,
        "ai_role_prompt": prompt,
        "status": "active",
        "turns": [],  # [{role: "user"|"ai", text: "..."}]
        "created_at": None,
    }

    with _lock:
        _sessions[session_id] = session

    logger.info("场景练习会话创建: %s (%s) - %s", session_id, st["label"], situation[:50])
    return {
        "session_id": session_id,
        "scenario_label": st["label"],
        "scenario_icon": st["icon"],
        "ai_role": ai_role,
        "situation": situation,
        "status": "active",
        "turn_count": 0,
    }


def get_session(session_id: str) -> dict | None:
    """获取会话状态."""
    return _sessions.get(session_id)


def record_turn(session_id: str, role: str, text: str):
    """供 chat.py 调用的对话记录 — SSE 流式回复后记录轮次."""
    session = _sessions.get(session_id)
    if session and session["status"] == "active":
        session["turns"].append({"role": role, "text": text})


def get_active_prompt(session_id: str) -> str | None:
    """获取场景练习的 system prompt，供 CognitiveBus 注入."""
    session = _sessions.get(session_id)
    if session and session["status"] == "active":
        return session.get("ai_role_prompt")
    return None


def _call_llm(messages: list[dict], max_tokens: int = 300) -> str | None:
    """调用 LLM. 返回内容或 None."""
    from app.utils import get_llm, get_llm_model

    client = get_llm()
    if not client:
        return None
    try:
        model = get_llm_model()
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        logger.warning("场景练习 LLM 调用失败", exc_info=True)
        return None


def scenario_respond(session_id: str, user_msg: str) -> dict:
    """AI 角色对用户消息的回应."""
    session = _sessions.get(session_id)
    if not session:
        return {"error": "会话不存在"}
    if session["status"] != "active":
        return {"error": "会话已结束，无法继续对话"}

    # 记录用户话语
    session["turns"].append({"role": "user", "text": user_msg})

    # 构建对话历史
    messages = [{"role": "system", "content": session["ai_role_prompt"]}]
    for turn in session["turns"]:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    # 调用 LLM 生成 AI 角色回应
    reply = _call_llm(messages, max_tokens=200)
    if not reply:
        return {"error": "LLM 调用失败，请稍后重试"}

    session["turns"].append({"role": "ai", "text": reply})
    return {"reply": reply, "turn_count": len([t for t in session["turns"] if t["role"] == "ai"])}


# 保持旧函数名兼容
client_respond = scenario_respond

# 随机场景 prompt
_RANDOM_PROMPT = """你是场景练习生成器。请随机生成一个社交场景练习。

场景类型从以下4种中选择:
- express_feelings: 表达感受（向某人说出内心真实感受）
- set_boundaries: 设立边界（对越界的人说"不"）
- resolve_conflict: 冲突化解（与有矛盾的人沟通）
- seek_support: 寻求支持（向人开口寻求帮助）

要求:
1. ai_role 要具体真实（如"男朋友""妈妈""同事小王""大学室友"等），不要泛泛的"对方"
2. situation 是一句话场景描述，有具体情境，让用户有代入感
3. scenario_type 随机选一种

输出 JSON 格式:
{{"scenario_type": "express_feelings", "ai_role": "男朋友", "situation": "你们最近沟通越来越少，你想告诉他你的不安"}}

只输出 JSON，不要其他。"""


def generate_random_scenario() -> dict:
    """调用 LLM 随机生成一个场景练习."""
    messages = [
        {"role": "system", "content": "你是一个场景生成器。只输出 JSON，不要 markdown 包裹。"},
        {"role": "user", "content": _RANDOM_PROMPT},
    ]
    raw = _call_llm(messages, max_tokens=400)
    if not raw:
        return {"error": "随机场景生成失败"}

    # 清理 markdown 代码块包裹
    raw = raw.strip()
    if raw.startswith("```"):
        # 去掉 ```json 或 ``` 开头
        first_nl = raw.find("\n")
        if first_nl > 0:
            raw = raw[first_nl + 1:]
        else:
            raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("随机场景 JSON 解析失败: %s", raw[:200])
        return {"error": "随机场景生成失败，请重试"}

    # 校验必要字段
    if not result.get("scenario_type") or not result.get("ai_role"):
        return {"error": "随机场景生成不完整，请重试"}

    # 校验 scenario_type 合法
    if result["scenario_type"] not in SCENARIO_TYPES:
        result["scenario_type"] = "express_feelings"

    return {
        "scenario_type": result["scenario_type"],
        "ai_role": result.get("ai_role", ""),
        "situation": result.get("situation", ""),
    }


def end_session(session_id: str) -> dict:
    """结束练习并生成反馈."""
    session = _sessions.get(session_id)
    if not session:
        return {"error": "会话不存在"}
    if session["status"] != "active":
        return {"error": "会话已结束"}

    user_turns = [t for t in session["turns"] if t["role"] == "user"]
    if not user_turns:
        return {"error": "还没有发送任何消息，无法生成反馈"}

    session["status"] = "feedback"

    # 构建对话记录文本
    dialogue_lines = []
    for turn in session["turns"]:
        role_label = "你" if turn["role"] == "user" else session["ai_role"]
        dialogue_lines.append(f"[{role_label}]: {turn['text']}")
    dialogue_text = "\n".join(dialogue_lines)

    # 调用 LLM 生成反馈
    prompt = _FEEDBACK_PROMPT.format(
        scenario_label=session["scenario_label"],
        situation=session.get("situation", ""),
        ai_role=session["ai_role"],
        dialogue=dialogue_text,
    )

    messages = [
        {"role": "system", "content": "你是一位人际沟通教练。只输出 JSON，不要有其他内容。"},
        {"role": "user", "content": prompt},
    ]

    feedback_raw = _call_llm(messages, max_tokens=800)
    if not feedback_raw:
        return {"error": "反馈生成失败"}

    # 清理可能的 markdown JSON 包裹
    if feedback_raw.startswith("```"):
        feedback_raw = feedback_raw.split("\n", 1)[1]
        if feedback_raw.endswith("```"):
            feedback_raw = feedback_raw[:-3]

    try:
        feedback = json.loads(feedback_raw)
    except json.JSONDecodeError:
        logger.warning("反馈 JSON 解析失败: %s", feedback_raw[:200])
        feedback = {
            "scores": {"clarity": 3, "awareness": 3, "boundary": 3, "assertiveness": 3, "perspective": 3},
            "highlights": ["完成了本次练习"],
            "improvements": ["可以更直接地表达自己的感受"],
            "overall": "每一次练习都是一次成长，继续加油！",
        }

    session["feedback"] = feedback
    return {
        "session_id": session_id,
        "scenario_label": session["scenario_label"],
        "ai_role": session["ai_role"],
        "turn_count": len([t for t in session["turns"] if t["role"] == "ai"]),
        "dialogue": session["turns"],
        "feedback": feedback,
    }
