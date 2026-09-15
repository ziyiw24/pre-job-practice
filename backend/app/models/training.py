"""上岗练 M0 数据模型。

这些模型与旧的健康题库分离，以便核心体验在不登录、不连数据库的
情况下独立运行。
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TrainingOption(BaseModel):
    key: str
    text: str


class Evidence(BaseModel):
    quote: str = Field(min_length=2, description="输入原文中的连续子串")
    start_offset: int | None = None
    end_offset: int | None = None
    page_number: int | None = None
    document_id: str | None = None
    block_id: str | None = None


RiskTag = Literal[
    "number",
    "temperature",
    "duration",
    "recipe",
    "safety",
    "punishment",
    "emergency",
]


class TrainingQuestion(BaseModel):
    id: str
    type: Literal["single", "judge"]
    scenario: str | None = None
    stem: str
    options: list[TrainingOption]
    answer: list[str]
    explanation: str
    knowledge_point: str
    evidence: Evidence
    risk_tags: list[RiskTag] = Field(default_factory=list)
    requires_confirmation: bool = False

    @model_validator(mode="after")
    def validate_answer(self):
        keys = [option.key for option in self.options]
        if len(keys) < 2 or len(keys) != len(set(keys)):
            raise ValueError("题目至少需要两个不重复选项")
        if len(self.answer) != 1 or self.answer[0] not in keys:
            raise ValueError("单选/判断题必须有且只有一个有效答案")
        return self


class TrainingQuiz(BaseModel):
    quiz_id: str
    title: str
    summary: str
    questions: list[TrainingQuestion]
    ai_generated: bool
    generation_mode: Literal["ai", "demo"]
    review_notice: str = "AI 生成内容需管理者确认，以门店最新正式制度为准。"


class TrainingGenerateRequest(BaseModel):
    client_request_id: str = Field(min_length=8, max_length=80)
    title: str = Field(default="", max_length=60)
    content: str = Field(min_length=500, max_length=8000)
    question_count: Literal[3, 5] = 5
    difficulty: Literal["easy", "mixed", "hard"] = "mixed"

    @model_validator(mode="after")
    def reject_unusable_content(self):
        compact = "".join(self.content.split())
        if len(set(compact)) < 12:
            raise ValueError("内容过于单一，请粘贴更完整的培训内容")
        return self


class TrainingTaskCreateResponse(BaseModel):
    task_id: str
    status: Literal["pending", "running", "awaiting_review", "completed", "failed"]


class TrainingAgentInfo(BaseModel):
    revision_count: int = 0
    max_revisions: int = 2
    issue_count: int = 0
    model_calls: int = 0
    graph_version: str = "training-author-v1"


class TrainingTaskStatusResponse(BaseModel):
    task_id: str
    status: Literal["pending", "running", "awaiting_review", "completed", "failed"]
    progress_stage: Literal["reading", "extracting", "planning", "generating", "validating", "reviewing", "rewriting", "awaiting_review"]
    agent: TrainingAgentInfo | None = None
    result: TrainingQuiz | None = None
    error_code: str | None = None
    error_message: str | None = None


class TrainingAnswerRecord(BaseModel):
    question_id: str
    selected_answers: list[str]
    duration_ms: int = Field(default=0, ge=0)


class TrainingReportRequest(BaseModel):
    quiz_id: str
    questions: list[TrainingQuestion]
    answer_records: list[TrainingAnswerRecord]


class TrainingReport(BaseModel):
    score: int = Field(ge=0, le=100)
    correct_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    result: Literal["passed", "needs_review"]
    mastered_points: list[str]
    weak_points: list[str]
    review_actions: list[str]
    ai_summary: str
    ai_generated: bool
    answer_results: dict[str, bool]
    certification_notice: str = "本结果仅用于在线学习，不等同于实操上岗认证。"


class TrainingDemoResponse(BaseModel):
    title: str
    content: str
