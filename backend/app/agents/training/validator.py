import re
from app.models.training import TrainingQuestion
from app.agents.training.state import ReviewIssue


def validate_questions(content: str, questions: list[dict], expected_count: int) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    if len(questions) != expected_count:
        issues.append({"question_id": "*", "code": "RULE_NOT_COVERED", "detail": "题量不符", "severity": "high"})
    for raw in questions:
        qid = str(raw.get("id", "*"))
        try:
            q = TrainingQuestion.model_validate(raw)
        except Exception as exc:
            issues.append({"question_id": qid, "code": "ANSWER_AMBIGUOUS", "detail": str(exc)[:160], "severity": "high"})
            continue
        quote = q.evidence.quote
        if quote not in content:
            issues.append({"question_id": qid, "code": "EVIDENCE_MISSING", "detail": "引用不在原文", "severity": "medium"})
            continue
        source_numbers = set(re.findall(r"\d+(?:\.\d+)?", quote))
        claimed_numbers = set(re.findall(r"\d+(?:\.\d+)?", f"{q.stem} {q.explanation}"))
        if not claimed_numbers.issubset(source_numbers):
            issues.append({"question_id": qid, "code": "NUMBER_CONFLICT", "detail": "题干或解析数字无原文依据", "severity": "high"})
        correct = next(o.text for o in q.options if o.key == q.answer[0])
        if len(correct) >= 8 and correct in q.stem:
            issues.append({"question_id": qid, "code": "OPTION_LEAKAGE", "detail": "题干泄露答案", "severity": "medium"})
    return issues
