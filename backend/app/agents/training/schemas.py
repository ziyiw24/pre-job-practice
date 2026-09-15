from typing import Literal
from pydantic import BaseModel, Field
from app.models.training import Evidence, RiskTag, TrainingQuestion


class ExtractedRule(BaseModel):
    rule_id: str
    category: Literal["procedure", "prohibition", "exception", "safety", "service"]
    statement: str
    evidence: Evidence
    risk_tags: list[RiskTag] = Field(default_factory=list)
    priority: Literal["must", "should", "optional"] = "should"


class RuleSet(BaseModel):
    rules: list[ExtractedRule]


class QuizPlanItem(BaseModel):
    question_id: str
    rule_id: str
    question_type: Literal["single", "judge"] = "single"
    scenario: str
    difficulty: Literal["easy", "mixed", "hard"] = "mixed"


class QuizPlan(BaseModel):
    items: list[QuizPlanItem]


class QuestionSet(BaseModel):
    questions: list[TrainingQuestion]


class ReviewIssueModel(BaseModel):
    question_id: str
    code: Literal["EVIDENCE_MISSING", "ANSWER_AMBIGUOUS", "NUMBER_CONFLICT", "OPTION_LEAKAGE", "RULE_NOT_COVERED", "UNSUPPORTED_CLAIM"]
    detail: str
    severity: Literal["low", "medium", "high"]


class CriticResult(BaseModel):
    issues: list[ReviewIssueModel] = Field(default_factory=list)


class TrainingReportSuggestion(BaseModel):
    ai_summary: str = Field(max_length=400)
    review_actions: list[str] = Field(min_length=1, max_length=3)
