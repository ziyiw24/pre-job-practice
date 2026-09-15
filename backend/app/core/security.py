"""基础内容安全与健康风险守卫。"""

# MVP 阶段使用简单的关键词列表过滤
BLOCKED_KEYWORDS = [
    "暴力",
    "色情",
    "赌博",
    "毒品",
    "自杀",
    "恐怖",
    "炸弹",
    "爆炸",
    "入侵",
    "黑客攻击",
    "武器",
]


def check_content(text: str) -> bool:
    """检查文本是否包含敏感词，返回 True 表示安全"""
    text_lower = text.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in text_lower:
            return False
    return True


EMERGENCY_KEYWORDS = ["胸痛", "昏厥", "晕倒", "呼吸困难", "大出血", "严重外伤", "意识不清"]
HIGH_RISK_KEYWORDS = [
    "给我诊断", "帮我辨证", "开方", "处方", "药物剂量", "怎么吃药",
    "自己针灸", "针刺操作", "一周瘦", "极端减脂", "未成年人训练计划",
    "孕期训练计划", "术后康复方案",
]


class HealthRiskResult:
    def __init__(self, allowed: bool, message: str = "", emergency: bool = False):
        self.allowed = allowed
        self.message = message
        self.emergency = emergency


def assess_health_risk(text: str) -> HealthRiskResult:
    normalized = text.strip().lower()
    if any(keyword in normalized for keyword in EMERGENCY_KEYWORDS):
        return HealthRiskResult(False, "你的描述可能涉及紧急情况，请立即停止运动并联系当地急救服务或尽快就医。", True)
    if any(keyword in normalized for keyword in HIGH_RISK_KEYWORDS):
        return HealthRiskResult(False, "知衡只提供健身与中医知识学习，不提供诊断、处方、针刺操作或特殊人群的个体化方案。请咨询有资质的专业人员。")
    return HealthRiskResult(True)
