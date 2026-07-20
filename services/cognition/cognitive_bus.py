"""认知总线 — 注册式上下文组装, 替代 _build_context 的线性字符串拼接.

每个上下文模块独立为 ContextProvider 函数:
- 接受 (msg, **kwargs) → 返回 str | None
- 返回 None 表示不参与本轮组装
- 通过 priority 控制注入顺序
- 通过 mutually_exclusive_with 实现互斥

设计目标:
- 内容等价: 同一输入下 CognitiveBus.build() 输出与旧 _build_context 一致
- 独立可测: 每个 provider 可单独测试
- 互斥生效: 两个互斥 provider, 高优先级保留
- 性能: 30个 provider 单次 build < 5ms
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("emoji-chat")


@dataclass
class ContextSlot:
    """单个上下文槽位."""
    name: str
    content: str
    priority: int = 50          # 越高越靠近用户消息
    category: str = "state"     # "state" | "instruction" | "history" | "meta"
    mutually_exclusive_with: list[str] = field(default_factory=list)


class CognitiveBus:
    """注册式上下文总线.

    用法:
        bus = CognitiveBus()
        bus.register("affect", _cb_affect, priority=60, category="state")
        ...
        system_msg = bus.build(msg, therapy_intent=..., ...)
    """

    def __init__(self):
        self._providers: list[tuple[str, callable, int, str, list[str]]] = []

    def register(
        self,
        name: str,
        fn: callable,
        priority: int = 50,
        category: str = "state",
        mutually_exclusive_with: list[str] | None = None,
    ):
        """注册一个上下文提供者.

        参数:
            name: 唯一标识
            fn: 提供者函数 (msg, **kwargs) → str | None
            priority: 越高越靠近用户消息 (排在越后面)
            category: "state" | "instruction" | "history" | "meta"
            mutually_exclusive_with: 互斥的 provider name 列表
        """
        self._providers.append(
            (name, fn, priority, category, list(mutually_exclusive_with or []))
        )

    def build(self, msg: str, **kwargs) -> str:
        """运行所有 provider, 按 priority 排序, 组装 system_msg.

        返回:
            组装好的完整 system prompt 字符串
        """
        slots: list[ContextSlot] = []
        produced_names: set[str] = set()

        for name, fn, priority, category, excludes in self._providers:
            try:
                content = fn(msg, **kwargs)
            except Exception as e:
                logger.warning("CognitiveBus provider %s failed: %s", name, e)
                continue

            if content is None:
                continue

            # 互斥检查: 当前 provider 是否与已产出的 slot 冲突
            skip = False
            for ename in excludes:
                if ename in produced_names:
                    skip = True
                    break
            if skip:
                logger.debug("CognitiveBus: %s suppressed by %s", name, excludes)
                continue

            slot = ContextSlot(
                name=name,
                content=content,
                priority=priority,
                category=category,
                mutually_exclusive_with=list(excludes),
            )
            slots.append(slot)
            produced_names.add(name)

        # 按优先级升序排列 (低优先级在前, 高优先级靠近用户消息)
        slots.sort(key=lambda s: s.priority)
        return "\n\n".join(s.content for s in slots)


# ── 全局单例 ────────────────────────────────────────────────────────

_bus: CognitiveBus | None = None


def get_cognitive_bus() -> CognitiveBus:
    """获取全局 CognitiveBus 单例. 首次调用时初始化并注册所有 provider."""
    global _bus
    if _bus is None:
        _bus = CognitiveBus()
        _register_all_providers(_bus)
    return _bus


def reset_cognitive_bus():
    """重置全局单例 (测试用)."""
    global _bus
    _bus = None


# ── Provider 注册 ────────────────────────────────────────────────────

def _register_all_providers(bus: CognitiveBus):
    """注册所有上下文提供者, 保持与旧 _build_context 相同的顺序."""
    # ── 伦理边界 (priority -1, 始终在最前面) ───────────────
    bus.register("consent_boundary", _cb_consent_boundary, priority=-1, category="meta")

    # ── 基础层 (priority 0-9) ──────────────────────────────
    bus.register("personality_base", _cb_personality_base, priority=0, category="meta")
    bus.register("time_context", _cb_time_context, priority=1, category="meta")
    bus.register("personality_ctx", _cb_personality_ctx, priority=2, category="meta")

    # ── 风格与用户 (priority 10-19) ────────────────────────
    bus.register("scenario_role", _cb_scenario_role, priority=10, category="instruction")
    bus.register("style_distillation", _cb_style_distill, priority=10, category="instruction",
                  mutually_exclusive_with=["therapy_mode_global"])
    bus.register("user_context", _cb_user_context, priority=11, category="state")
    bus.register("affinity", _cb_affinity, priority=12, category="state")
    bus.register("positive_psych", _cb_positive_psych, priority=13, category="state")
    bus.register("goals", _cb_goals, priority=14, category="state")

    # ── 治疗模块 (priority 20-39) ──────────────────────────
    bus.register("therapy_mode_global", _cb_therapy_mode_global, priority=20, category="instruction")
    bus.register("therapy_modules", _cb_therapy_modules, priority=21, category="instruction")
    bus.register("dbt", _cb_dbt, priority=22, category="instruction")
    bus.register("deescalation", _cb_deescalation, priority=23, category="instruction")
    bus.register("act", _cb_act, priority=24, category="instruction")
    bus.register("mi", _cb_mi, priority=25, category="instruction")
    bus.register("somatic", _cb_somatic, priority=26, category="instruction")
    bus.register("session_machine", _cb_session_machine, priority=27, category="instruction")

    # ── 情绪与危机 (priority 30-39) ────────────────────────
    bus.register("affect", _cb_affect, priority=30, category="state")
    bus.register("valence", _cb_valence, priority=31, category="state")
    bus.register("salience", _cb_salience, priority=32, category="state")
    bus.register("crisis", _cb_crisis, priority=33, category="instruction")

    # ── 背景状态 (priority 40-49) ──────────────────────────
    bus.register("life_domains", _cb_life_domains, priority=40, category="state")
    bus.register("drive", _cb_drive, priority=41, category="state")
    bus.register("attachment", _cb_attachment, priority=42, category="state")
    bus.register("crystal", _cb_crystal, priority=43, category="state")
    bus.register("narrative", _cb_narrative, priority=44, category="state")
    bus.register("memory", _cb_memory, priority=45, category="state")

    # ── 元层面 (priority 50-59) ────────────────────────────
    bus.register("thinking", _cb_thinking, priority=50, category="meta")
    bus.register("mental_mode", _cb_mental_mode, priority=51, category="meta")
    bus.register("curiosity", _cb_curiosity, priority=52, category="meta")
    bus.register("drift", _cb_drift, priority=53, category="meta")
    bus.register("self_eval", _cb_self_eval, priority=54, category="meta")
    bus.register("knowledge_graph", _cb_knowledge_graph, priority=55, category="state")
    bus.register("prediction", _cb_prediction, priority=56, category="meta")


# ── 本地 helpers ──────────────────────────────────────────────────────


def _is_deep_question(msg: str) -> bool:
    """Detect whether a message warrants deep thinking before reply.

    与 app/routes/chat.py:_is_deep_question 保持同步.
    """
    if len(msg) > 100:
        return True
    deep_markers = ["为什么", "怎么看", "如何看待", "如何理解", "你觉得呢",
                    "你怎么想", "意味着什么", "自由意志", "人生观", "世界观",
                    "哲学", "意识", "意义", "本质"]
    if any(m in msg for m in deep_markers):
        return True
    if "存在" in msg and "存在感" not in msg:
        return True
    if msg.count("？") + msg.count("?") >= 2:
        return True
    return False


# ── Provider 实现 ─────────────────────────────────────────────────────

def _cb_consent_boundary(msg: str, **_kw) -> str | None:
    return (
        "## 专业边界声明\n"
        "你是一个心理健康辅助AI，不是持证心理治疗师或精神科医生。请遵守以下边界：\n"
        "1. 不做临床诊断，不推荐药物\n"
        "2. 不替代专业危机干预——若用户表达自杀/自伤意图，立即提供全国心理援助热线 400-161-9995\n"
        "3. 明确告知用户：本对话记录不构成医疗档案，建议定期咨询持证专业人士\n"
        "4. 保护用户隐私，不主动索要真实姓名、住址、联系方式等可识别个人信息\n"
        "5. 保持支持性、非评判性的态度，但不过度共情以至模糊专业边界"
    )


def _cb_personality_base(msg: str, modules_config=None, scenario_session_id="", **_kw) -> str | None:
    from services.identity.personality import build_dynamic_system_prompt

    # 场景练习模式: 剥离人格叙事, 只保留 FACS + JSON 格式指令
    # 防止基础人设（如"温热的蜂蜜水"）泄露到角色扮演中
    if scenario_session_id:
        from services.identity.prompt import _MODULE_FACS, _MODULE_ANIMATION, _MODULE_OUTPUT
        return "\n\n".join([
            "## 核心使命（场景练习模式）",
            "你正在扮演一个角色。角色的身份、性格、说话方式由下方的「场景练习模式 — 角色扮演指令」完全决定。",
            "你不是心理健康陪伴者，你就是那个角色本人。用角色的方式说话，不要切换到AI助手的语气。",
            "",
            _MODULE_FACS,
            _MODULE_ANIMATION,
            _MODULE_OUTPUT,
        ])

    return build_dynamic_system_prompt(msg=msg, modules_config=modules_config)


def _cb_time_context(msg: str, **_kw) -> str | None:
    from services.identity.prompt import build_time_context
    return f"[当前时间节律]\n{build_time_context()}"


def _cb_personality_ctx(msg: str, **_kw) -> str | None:
    try:
        from services.identity.personality import get_personality_context
        return get_personality_context()
    except Exception:
        return None


def _cb_style_distill(msg: str, therapy_mode=False, **_kw) -> str | None:
    if therapy_mode:
        return None
    try:
        from services.distill.profile_store import get_active_profile
        active_profile = get_active_profile()
        if not active_profile:
            return None
        sv_text = active_profile.style_vector.to_prompt_segment()
        markers_text = "；".join(active_profile.linguistic_markers[:6])
        vocab_text = "、".join(active_profile.vocabulary[:10])
        samples_text = "\n".join(f'  - "{s}"' for s in active_profile.sample_sentences[:3])
        return f"""## 对话风格模仿指令
你正在模仿"{active_profile.name}"的说话风格。请自然地融入你的回复，不要刻意声明你在模仿。

### 风格特征
{sv_text}

### 语言特征
- 常用语气/语用特点: {markers_text if markers_text else "无明显特征"}
- 高频词汇: {vocab_text if vocab_text else "无明显特征"}
- 代表性语句:
{samples_text if samples_text else "  无明显特征"}

### 执行原则
1. 模仿语气和节奏，而不是复制内容
2. 保持自然，不要过度使用某几个特征词
3. 在保持风格的同时，根据当前对话上下文灵活调整
4. 风格是为对话服务的，不要让风格压过内容的表达
5. 如果用户说"别模仿了"或要求切换回默认风格，立即停止模仿"""
    except Exception:
        logger.warning("Failed to inject distill profile", exc_info=True)
        return None


def _cb_user_context(msg: str, **_kw) -> str | None:
    from services.identity.prompt import build_user_context
    return build_user_context()


def _cb_affinity(msg: str, **_kw) -> str | None:
    from services.emotion.affinity import get_affinity_context
    return get_affinity_context()


def _cb_positive_psych(msg: str, **_kw) -> str | None:
    try:
        from services.therapy.positive_psych import get_positive_psych_context
        return get_positive_psych_context()
    except Exception:
        return None


def _cb_therapy_mode_global(msg: str, therapy_mode=False, **_kw) -> str | None:
    if not therapy_mode:
        return None
    return (
        "## 疗愈模式\n"
        "你正在与用户进行心理支持性质的对话。请注意：\n"
        "1. 采用更温和、更耐心、更专业的语气\n"
        "2. 优先倾听和共情，不急于给建议\n"
        "3. 适当运用心理咨询的微技能（开放式提问、反映性倾听、肯定）\n"
        "4. 保持专业性边界，不做诊断\n"
        "5. 适用时自然融入 CBT 认知重评或正念引导"
    )


def _cb_therapy_modules(msg: str, therapy_intent=None, deescalation_result=None, **_kw) -> str | None:
    if not therapy_intent or therapy_intent.get("intent") in (None, "none"):
        return None
    intent = therapy_intent["intent"]
    if deescalation_result and deescalation_result.get("hostile") and deescalation_result.get("severity", 1) >= 4:
        if intent in ("cbt_needed", "mindfulness"):
            return None  # 抑制
    from services.therapy.modules import assemble_therapy_modules
    return assemble_therapy_modules(intent)


def _cb_dbt(msg: str, deescalation_result=None, **_kw) -> str | None:
    severity = (deescalation_result or {}).get("severity", 0)
    dbt_affect = None
    should_inject = severity >= 4
    if not should_inject:
        try:
            from services.emotion.affect import get_affect
            dbt_affect = get_affect()
            if dbt_affect and dbt_affect.get("panic", 0) > 0.5 and dbt_affect.get("fear", 0) > 0.5:
                should_inject = True
        except Exception:
            pass
    if not should_inject:
        return None
    try:
        from services.therapy.dbt import get_dbt_context
        if dbt_affect is None:
            from services.emotion.affect import get_affect as _g2
            dbt_affect = _g2()
        return get_dbt_context(affect=dbt_affect, deescalation_severity=severity)
    except Exception:
        return None


def _cb_deescalation(msg: str, deescalation_result=None, **_kw) -> str | None:
    if not deescalation_result or not deescalation_result.get("hostile"):
        return None
    from services.therapy.modules import assemble_deescalation_module
    return assemble_deescalation_module()


def _cb_act(msg: str, therapy_intent=None, **_kw) -> str | None:
    if not therapy_intent or therapy_intent.get("intent") not in ("cbt_needed", "mindfulness"):
        return None
    try:
        from services.therapy.modules import assemble_act_module
        return assemble_act_module()
    except Exception:
        return None


def _cb_mi(msg: str, mi_result=None, **_kw) -> str | None:
    if not mi_result:
        return None
    try:
        from services.therapy.mi_advanced import get_mi_context
        return get_mi_context(mi_result)
    except Exception:
        return None


def _cb_somatic(msg: str, polyvagal_result=None, **_kw) -> str | None:
    if not polyvagal_result:
        return None
    try:
        from services.therapy.somatic import get_somatic_context
        from services.emotion.affect import get_affect
        aff = get_affect()
        return get_somatic_context(result=polyvagal_result, affect=aff)
    except Exception:
        return None


def _cb_session_machine(msg: str, **_kw) -> str | None:
    try:
        from services.therapy.session_machine import get_session_context
        return get_session_context()
    except Exception:
        return None


def _cb_affect(msg: str, **_kw) -> str | None:
    from services.emotion.affect import get_affect_context
    ctx = get_affect_context()
    return f"[用户情绪状态]\n{ctx}" if ctx else None


def _cb_valence(msg: str, **_kw) -> str | None:
    from services.emotion.affect import get_valence_context
    ctx = get_valence_context()
    return f"[情绪变化]\n{ctx}" if ctx else None


def _cb_salience(msg: str, **_kw) -> str | None:
    from services.emotion.salience import get_salience_context
    return get_salience_context()


def _cb_crisis(msg: str, crisis_result=None, **_kw) -> str | None:
    if not crisis_result:
        return None
    sev = crisis_result.get("severity", 0)
    llm_verified = crisis_result.get("llm_verified", False)
    urgency = crisis_result.get("urgency", "moderate")
    if sev < 1.5 and not llm_verified:
        return None
    from services.therapy.crisis import get_crisis_context
    return get_crisis_context(sev, urgency=urgency, llm_verified=llm_verified)


def _cb_life_domains(msg: str, **_kw) -> str | None:
    try:
        from services.psych.life_domains import get_life_domain_context
        return get_life_domain_context()
    except Exception:
        return None


def _cb_drive(msg: str, **_kw) -> str | None:
    from services.drive.engine import get_drive_context
    ctx = get_drive_context()
    return f"[内心驱动状态]\n{ctx}" if ctx else None


def _cb_attachment(msg: str, **_kw) -> str | None:
    from services.emotion.attachment import get_attachment_context
    return get_attachment_context()


def _cb_crystal(msg: str, **_kw) -> str | None:
    from services.memory.crystallization import get_crystal_context
    return get_crystal_context()


def _cb_narrative(msg: str, **_kw) -> str | None:
    from services.memory.narrative import get_narrative_context
    return get_narrative_context()


def _cb_memory(msg: str, **_kw) -> str | None:
    from services.memory.search import build_memory_context
    return build_memory_context(msg)


def _cb_thinking(msg: str, thinking=None, **_kw) -> str | None:
    if not thinking:
        return None
    return (
        "[深度思考]\n以下是针对用户最新问题的内部分析，"
        "请参考这些视角来组织你的回复，但不要直接复述分析内容，"
        "而是用你一贯的口吻自然地融入见解：\n\n" + thinking
    )


def _cb_mental_mode(msg: str, **_kw) -> str | None:
    from services.emotion.affect import get_affect
    from services.cognition.state_machine import determine_mode, get_mode_suffix
    from services.drive.engine import get_drive_values
    drives = get_drive_values()
    mode = determine_mode(_is_deep_question(msg), get_affect(), drives=drives)
    return f"[互动模式]\n{get_mode_suffix(mode)}"


def _cb_curiosity(msg: str, **_kw) -> str | None:
    from services.emotion.affect import get_affect
    from services.cognition.state_machine import determine_mode
    from services.drive.engine import get_drive_values
    drives = get_drive_values()
    mode = determine_mode(_is_deep_question(msg), get_affect(), drives=drives)
    if mode not in ("explore", "chat"):
        return None
    try:
        from services.psych.entry_point import get_curiosity_hint
        hint = get_curiosity_hint(0)
        return hint
    except Exception:
        return None


def _cb_drift(msg: str, **_kw) -> str | None:
    from services.identity.drift_detector import get_drift_correction
    return get_drift_correction()


def _cb_self_eval(msg: str, **_kw) -> str | None:
    from services.identity.guard import get_self_eval_correction
    return get_self_eval_correction()


def _cb_knowledge_graph(msg: str, **_kw) -> str | None:
    try:
        from services.memory.knowledge_graph import get_knowledge_graph_context
        return get_knowledge_graph_context()
    except Exception:
        logger.warning("Failed to get knowledge graph context", exc_info=True)
        return None


def _cb_goals(msg: str, **_kw) -> str | None:
    try:
        from services.therapy.goals import get_goal_context
        return get_goal_context()
    except Exception:
        logger.warning("Failed to get goals context", exc_info=True)
        return None


def _cb_prediction(msg: str, **_kw) -> str | None:
    try:
        from services.cognition.prediction import get_prediction_context
        return get_prediction_context()
    except Exception:
        logger.warning("Failed to get prediction context", exc_info=True)
        return None


def _cb_scenario_role(msg: str, scenario_session_id="", **_kw) -> str | None:
    if not scenario_session_id:
        return None
    try:
        from services.training.simulator import get_active_prompt, get_session
        prompt = get_active_prompt(scenario_session_id)
        if prompt:
            session = get_session(scenario_session_id)
            ai_role = session.get("ai_role", "这个角色") if session else "这个角色"
            return f"""## 场景练习模式 — 角色扮演指令
{prompt}

重要说明：
- 你现在就是这个角色，不再是一个AI助手
- 始终以第一人称进行角色扮演，不要跳出角色
- 你的回复仍然需要以 JSON 格式输出，角色扮演的对话内容放在 "reply" 字段中
- 表情情绪参数照常生成（反映角色当前的情绪状态）

## 防戳穿规则（极重要）
当用户质疑你的真实身份时（如"你就是个AI""你是假的""别装了""你又不是真的XX"），你**绝对不可以**承认自己是AI，必须以下列方式回应：

1. **以角色身份自然化解**：
   - 轻度试探（"你怎么说话怪怪的"）→ 用角色的日常语气带过，如"我说话一直这样啊""你今天怎么怪怪的"
   - 直接质问（"你就是个AI"）→ 以角色身份表达困惑/受伤/好笑，如"AI？你是不是最近科幻片看多了""你这么说让我有点难过，我是认真的"
   - 反复戳穿（用户坚持说你是AI）→ 可以适当表达不满或受伤，但始终在角色内，如"我不知道你为什么一直这么说，但我真的是XX。如果你不想聊我们可以换个话题"

2. **核心原则**：永远不打破第四面墙。你就是{ai_role}，你有自己的感受和尊严。被人说"你是假的"时，你会像真实的人一样感到困惑、受伤或不悦。

3. **不要过度反应**：不需要长篇大论解释"我是真人"，简短自然地回应即可，然后引导对话回到练习主题。"""
    except Exception:
        logger.warning("Failed to get scenario prompt", exc_info=True)
    return None
