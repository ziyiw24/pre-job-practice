from typing import Literal, TypedDict


class ReviewIssue(TypedDict):
    question_id: str
    code: Literal["EVIDENCE_MISSING", "ANSWER_AMBIGUOUS", "NUMBER_CONFLICT", "OPTION_LEAKAGE", "RULE_NOT_COVERED", "UNSUPPORTED_CLAIM"]
    detail: str
    severity: Literal["low", "medium", "high"]


class TrainingAgentState(TypedDict, total=False):
    task_id: str
    title: str
    content: str
    question_count: int
    difficulty: str
    extracted_rules: list[dict]
    quiz_plan: list[dict]
    questions: list[dict]
    deterministic_issues: list[ReviewIssue]
    critic_issues: list[ReviewIssue]
    revision_count: int
    max_revisions: int
    token_usage: int
    model_calls: int
    max_model_calls: int
    status: Literal["running", "awaiting_review", "completed", "failed"]
    prompt_version: str
    graph_version: str
    result: dict
