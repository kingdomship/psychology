"""临床评估量表 — PHQ-9 (抑郁) + GAD-7 (焦虑) 题库与计分."""

import logging

logger = logging.getLogger("emoji-chat")

# ── PHQ-9 患者健康问卷抑郁量表 ──
PHQ9_QUESTIONS = [
    {"id": 1, "text": "做事时提不起劲或没有兴趣", "domain": "anhedonia"},
    {"id": 2, "text": "感到心情低落、沮丧或绝望", "domain": "depressed_mood"},
    {"id": 3, "text": "入睡困难、睡不安稳或睡眠过多", "domain": "sleep"},
    {"id": 4, "text": "感觉疲倦或没有活力", "domain": "fatigue"},
    {"id": 5, "text": "食欲不振或吃太多", "domain": "appetite"},
    {"id": 6, "text": "觉得自己很糟，或觉得自己很失败，或让家人失望", "domain": "self_esteem"},
    {"id": 7, "text": "做事时难以集中注意力，例如阅读报纸或看电视", "domain": "concentration"},
    {"id": 8, "text": "动作或说话速度缓慢到别人已察觉？或正好相反——比平时更烦躁或坐立不安", "domain": "psychomotor"},
    {"id": 9, "text": "有不如死掉或用某种方式伤害自己的念头", "domain": "suicidal"},
]

PHQ9_OPTIONS = [
    {"score": 0, "label": "完全没有"},
    {"score": 1, "label": "有几天"},
    {"score": 2, "label": "一半以上天数"},
    {"score": 3, "label": "几乎每天"},
]


def interpret_phq9(score: int) -> dict:
    """PHQ-9 分数解释."""
    if score <= 4:
        level = "无或极轻微抑郁症状"
        suggestion = "目前状态良好，请继续保持健康的生活方式。"
    elif score <= 9:
        level = "轻度抑郁"
        suggestion = "建议关注情绪变化，尝试增加日常活动和社交。如症状持续，考虑咨询专业人士。"
    elif score <= 14:
        level = "中度抑郁"
        suggestion = "建议寻求心理咨询或治疗。CBT认知行为疗法对中度抑郁有较好效果。"
    elif score <= 19:
        level = "中重度抑郁"
        suggestion = "强烈建议尽快咨询精神科医生或心理治疗师，可能需要结合药物治疗与心理治疗。"
    else:
        level = "重度抑郁"
        suggestion = "请立即联系精神科医生或拨打心理援助热线 400-161-9995。你不需要一个人面对。"
    return {"score": score, "level": level, "suggestion": suggestion, "max_score": 27}


# ── GAD-7 广泛性焦虑障碍量表 ──
GAD7_QUESTIONS = [
    {"id": 1, "text": "感到紧张、焦虑或不安"},
    {"id": 2, "text": "无法停止或控制担忧"},
    {"id": 3, "text": "过分担忧各种事情"},
    {"id": 4, "text": "难以放松"},
    {"id": 5, "text": "坐立不安，难以安静坐着"},
    {"id": 6, "text": "变得容易烦躁或急躁"},
    {"id": 7, "text": "感到害怕，好像有什么可怕的事会发生"},
]

GAD7_OPTIONS = [
    {"score": 0, "label": "完全没有"},
    {"score": 1, "label": "有几天"},
    {"score": 2, "label": "一半以上天数"},
    {"score": 3, "label": "几乎每天"},
]


def interpret_gad7(score: int) -> dict:
    """GAD-7 分数解释."""
    if score <= 4:
        level = "无或极轻微焦虑症状"
        suggestion = "目前的焦虑水平在正常范围内。"
    elif score <= 9:
        level = "轻度焦虑"
        suggestion = "建议练习正念冥想或深呼吸等放松技巧。如果症状持续，可以寻求专业帮助。"
    elif score <= 14:
        level = "中度焦虑"
        suggestion = "建议寻求心理咨询。正念认知疗法(MBCT)和CBT对焦虑有良好效果。"
    else:
        level = "重度焦虑"
        suggestion = "强烈建议咨询精神科医生或心理治疗师。严重焦虑可能显著影响日常生活功能。"
    return {"score": score, "level": level, "suggestion": suggestion, "max_score": 21}


# ── 量表注册表 ──
SCALES = {
    "phq9": {
        "name": "PHQ-9 抑郁筛查",
        "questions": PHQ9_QUESTIONS,
        "options": PHQ9_OPTIONS,
        "interpret": interpret_phq9,
        "total_questions": 9,
    },
    "gad7": {
        "name": "GAD-7 焦虑筛查",
        "questions": GAD7_QUESTIONS,
        "options": GAD7_OPTIONS,
        "interpret": interpret_gad7,
        "total_questions": 7,
    },
}
