"""可重现的本地模型替身，用于无 API Key 的开发和评测。"""
import re
from typing import Any

from app.agents.training.schemas import CriticResult, QuestionSet, QuizPlan, RuleSet


class MockTrainingModelGateway:
    def __init__(self):
        self.calls: list[dict] = []

    async def generate_structured(self, **kwargs) -> Any:
        self.calls.append(kwargs)
        schema = kwargs["output_schema"]
        payload = kwargs.get("context", {})
        if schema is RuleSet:
            content = payload["content"]
            chunks = [x.strip(" ，,") for x in re.split(r"[\n。！；;]+", content) if len(x.strip()) >= 10]
            rules = []
            for i, text in enumerate(chunks):
                if re.search(r"必须|不得|严禁|需|应|立即|才可", text):
                    start = content.find(text)
                    tags = []
                    for tag, pattern in [("number", r"\d"), ("temperature", r"温度|℃"), ("duration", r"小时|分钟|时效|时间"), ("recipe", r"配方|糖度|杯型"), ("safety", r"安全|消毒|污染|异味|隔离"), ("punishment", r"处罚|扣款"), ("emergency", r"立即|火灾|漏电|烫伤")]:
                        if re.search(pattern, text): tags.append(tag)
                    rules.append({"rule_id": f"r{len(rules)+1}", "category": "safety" if "safety" in tags else "procedure", "statement": text, "evidence": {"quote": text, "start_offset": start, "end_offset": start + len(text)}, "risk_tags": tags, "priority": "must" if re.search(r"必须|不得|严禁", text) else "should"})
            return RuleSet.model_validate({"rules": rules})
        if schema is QuizPlan:
            rules, count = payload["rules"], payload["question_count"]
            ordered = sorted(rules, key=lambda r: (r.get("priority") != "must", "safety" not in r.get("risk_tags", [])))
            return QuizPlan.model_validate({"items": [{"question_id": f"q{i+1}", "rule_id": ordered[i % len(ordered)]["rule_id"], "scenario": "你在当班中遇到了这种情况。", "difficulty": payload["difficulty"]} for i in range(count)]})
        if schema is QuestionSet:
            rules = {r["rule_id"]: r for r in payload["rules"]}
            questions = []
            for item in payload["plan"]:
                rule = rules[item["rule_id"]]; quote = rule["evidence"]["quote"]
                options = [{"key": "A", "text": quote}, {"key": "B", "text": "先继续操作，交班时再处理"}, {"key": "C", "text": "由员工根据经验自行决定"}, {"key": "D", "text": "无需记录或报告"}]
                questions.append({"id": item["question_id"], "type": "single", "scenario": item["scenario"], "stem": "根据培训内容，下列哪项做法正确？", "options": options, "answer": ["A"], "explanation": f"原文要求：{quote}。", "knowledge_point": quote[:18], "evidence": rule["evidence"], "risk_tags": rule["risk_tags"], "requires_confirmation": bool(rule["risk_tags"])})
            return QuestionSet.model_validate({"questions": questions})
        if schema is CriticResult:
            return CriticResult(issues=[])
        raise TypeError(f"unsupported schema: {schema}")
