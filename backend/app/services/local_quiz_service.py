"""Deterministic, source-grounded quiz fallback for local development.

It keeps the complete learning loop usable without an external model key. The
production LLM path still uses the same reviewed topic context.
"""

from app.models.quiz import Question, QuestionOption, QuizOutput
from app.models.topic import Topic


CURATED: dict[str, list[dict]] = {
    "topic_gallbladder_meridian": [
        {"stem": "足少阳胆经在中医理论中属于什么？", "correct": "十二经脉之一", "wrong": ["一块肌肉", "一条血管", "一种西药"], "point": "胆经的基本定位", "explanation": "足少阳胆经是中医十二经脉之一，应在中医理论语境中理解。"},
        {"stem": "根据审核资料，胆经循行的起始部位接近哪里？", "correct": "眼外角", "wrong": ["手掌中心", "肚脐", "足底中心"], "point": "胆经循行概要", "explanation": "审核内容将其概括为从眼外角附近开始，再经头侧、耳后、颈肩等部位。"},
        {"stem": "胆经在下肢的循行概要更接近哪一项？", "correct": "沿下肢外侧向下", "wrong": ["沿下肢内侧向上", "仅环绕膝关节", "仅位于足底"], "point": "胆经循行概要", "explanation": "审核内容描述其沿下肢外侧向下，至足第四趾外侧端。"},
        {"stem": "学习胆经知识时，哪种理解是正确的？", "correct": "它是中医理论知识，不能用来自我诊断", "wrong": ["看循行就能确诊疾病", "任何疼痛都是胆经问题", "可以代替医生面诊"], "point": "学习边界", "explanation": "经络知识用于学习中医理论，不构成个人诊断或治疗方案。"},
        {"stem": "关于胆经穴位与针刺，哪项更符合安全边界？", "correct": "精确定位和针刺应由受过训练的专业人员进行", "wrong": ["看一张图就可自行针刺", "针刺越深效果越好", "所有人都适合相同穴位"], "point": "针刺安全边界", "explanation": "穴位精确定位和针刺需要专业训练，本产品不提供针刺操作指导。"},
    ],
    "topic_moxibustion": [
        {"stem": "艾灸在中医知识中更接近以下哪个概念？", "correct": "使用艾绒或艾制品热力作用于体表特定部位的灸法", "wrong": ["一种口服药物", "一种力量训练", "一种影像检查"], "point": "艾灸概念", "explanation": "艾灸属于中医灸法，其特征是艾绒或艾制品所产生的热力刺激。"},
        {"stem": "艾灸时是否温度越高、时间越长越好？", "correct": "不是，过热或过久会增加烫伤风险", "wrong": ["是，只要忍住就行", "是，水疱越大越好", "与温度和时间完全无关"], "point": "热损伤风险", "explanation": "艾灸存在低温烫伤等风险，不应追求过高温度或过长时间。"},
        {"stem": "以下哪项是艾灸需要注意的风险？", "correct": "烫伤、烟雾刺激与火灾", "wrong": ["骨骼立即变长", "视力必然提升", "完全不会出现皮肤反应"], "point": "艾灸安全风险", "explanation": "热源、明火、烟雾和皮肤反应都是艾灸中需要识别的安全问题。"},
        {"stem": "艾灸后出现灼痛、水疱或持续红肿时，更合适的做法是什么？", "correct": "停止操作并联系医护人员", "wrong": ["继续加热", "立即刺破所有水疱", "完全忽略"], "point": "不良反应处置", "explanation": "明显灼痛、水疱或持续红肿不应被当作“效果越好”，应停止并寻求专业意见。"},
        {"stem": "对医疗性艾灸的安全定位，哪项正确？", "correct": "应由正规医疗机构的专业人员评估和操作", "wrong": ["所有人都可照视频自行治病", "可用来替代必要的就医", "不需要考虑个体差异"], "point": "专业操作边界", "explanation": "艾灸知识学习不等于治疗指导；医疗性操作需要专业评估。"},
    ],
}


def _options(correct: str, wrong: list[str], question_index: int) -> tuple[list[QuestionOption], str]:
    values = [correct, *wrong]
    shift = (question_index - 1) % len(values)
    values = values[-shift:] + values[:-shift] if shift else values
    options = [QuestionOption(key=key, text=text) for key, text in zip("ABCD", values)]
    answer = next(option.key for option in options if option.text == correct)
    return options, answer


def generate_local_quiz(topic: Topic, question_count: int, difficulty: str) -> QuizOutput:
    items = list(CURATED.get(topic.id, []))
    if not items:
        first_fact = topic.content.split("。")[0] + "。"
        items = [
            {"stem": f"关于「{topic.title}」，哪项符合审核内容？", "correct": first_fact, "wrong": ["可用一条知识自我诊断", "所有人都应采用相同做法", "资料来源和安全边界都不重要"], "point": topic.title, "explanation": first_fact},
            {"stem": "本专题的内容定位是什么？", "correct": "健康知识学习，不替代专业医疗意见", "wrong": ["个人疾病诊断", "处方与用药指导", "不经评估的治疗方案"], "point": "内容边界", "explanation": "知衡用于知识学习，不提供诊断、处方或个性化治疗。"},
            {"stem": "阅读健康知识时，哪个做法更可取？", "correct": "查看来源并注意内容的适用边界", "wrong": ["只看标题就做医疗决定", "忽略更新时间", "将科普当成医生诊断"], "point": "信息素养", "explanation": "来源、审核状态、更新时间和适用边界都是判断健康内容的重要信息。"},
            {"stem": "出现胸痛、昏厥或呼吸困难等危险描述时应怎么做？", "correct": "停止活动并尽快寻求急救或就医", "wrong": ["继续训练观察", "只依赖网络问答", "自行加大操作强度"], "point": "紧急就医", "explanation": "危险症状不属于普通学习问题，应优先获得及时医疗帮助。"},
            {"stem": f"本专题的主要审核来源是哪一个？", "correct": topic.sources[0].publisher, "wrong": ["匿名论坛", "无出处的转载", "个人营销广告"], "point": "知识来源", "explanation": f"本专题标注的来源为：{topic.sources[0].publisher}《{topic.sources[0].title}》。"},
        ]

    while len(items) < question_count:
        items.append(items[len(items) % len(items)].copy())

    questions = []
    level = topic.difficulty if difficulty == "mixed" else difficulty
    source_refs = [f"{source.publisher}·{source.title}" for source in topic.sources]
    for index, item in enumerate(items[:question_count], 1):
        options, answer = _options(item["correct"], item["wrong"], index)
        questions.append(Question(
            id=f"q{index}", type="single", stem=item["stem"],
            options=options, answer=[answer],
            explanation=item["explanation"], knowledge_point=item["point"],
            difficulty=level, domain=topic.category,
            source_refs=source_refs, risk_level=topic.risk_level,
        ))
    return QuizOutput(title=topic.title, summary=topic.summary, questions=questions)
