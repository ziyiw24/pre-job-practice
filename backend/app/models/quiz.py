"""题库相关数据模型"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class QuestionOption(BaseModel):
    key: str = Field(description="选项标识，如 A、B、C、D")
    text: str = Field(description="选项文本")


class Question(BaseModel):
    id: str = Field(description="题目编号，如 q1")
    type: Literal["single", "multiple", "judge"] = Field(description="题型")
    stem: str = Field(description="题干")
    options: list[QuestionOption] = Field(description="选项列表")
    answer: list[str] = Field(description="正确答案的 key 列表")
    explanation: str = Field(description="详细讲解")
    knowledge_point: str = Field(description="知识点标签")
    difficulty: Literal["easy", "medium", "hard"] = Field(description="难度")
    image_url: str | None = Field(default=None, description="AI 生成的题目配图 URL（可选）")
    domain: Literal["fitness", "tcm", "safety", "general"] = Field(default="general", description="内容领域")
    source_refs: list[str] = Field(default_factory=list, description="题目依据的来源标题")
    risk_level: Literal["low", "medium", "high"] = Field(default="low", description="健康内容风险级别")


class QuizOutput(BaseModel):
    """AI 生成题库的结构化输出 Schema"""

    title: str = Field(description="学习主题")
    summary: str = Field(description="本次题库的主题摘要")
    questions: list[Question] = Field(description="题目列表")


class QuizGenerateRequest(BaseModel):
    user_input: str = Field(
        default="",
        max_length=2000,
        description="自然语言学习意图，服务端仅匹配已审核的本地知识专题",
    )
    topic_id: str | None = Field(default=None, description="已审核精选专题 ID")
    question_count: int = Field(default=5, ge=3, le=10, description="题目数量")
    difficulty: Literal["easy", "medium", "hard", "mixed"] = Field(
        default="mixed", description="难度"
    )
    doc_id: str | None = Field(
        default=None, description="可选，指定基于某篇知识库文档出题"
    )
    generate_images: bool = Field(
        default=False, description="是否为每道题目生成配图"
    )

    @model_validator(mode="after")
    def require_controlled_source(self):
        if not self.topic_id and not self.doc_id and not self.user_input.strip():
            raise ValueError("请输入想学的知识点，或选择已审核专题")
        if self.doc_id and not self.user_input.strip():
            raise ValueError("基于用户知识库出题时需要检索词")
        return self


class QuizGenerateResponse(BaseModel):
    quiz_id: str
    title: str
    summary: str
    questions: list[Question]
    topic_id: str | None = None
    domain: Literal["fitness", "tcm", "safety", "general"] = "general"
    source_refs: list[str] = Field(default_factory=list)
    health_notice: str = "内容仅供知识学习，不替代专业医疗意见。"
    image_notice: str | None = Field(
        default=None, description="配图相关的提示信息（如未登录/额度已用完/部分题目未配图等），无异常时为 None"
    )


class AnswerRecord(BaseModel):
    question_id: str
    selected_answers: list[str]
    is_correct: bool
    duration_ms: int = Field(ge=0)


# ---- 异步任务模型 ----

class QuizTaskCreateResponse(BaseModel):
    """创建出题任务的响应"""
    task_id: str


class QuizTaskStatusResponse(BaseModel):
    """轮询任务状态的响应"""
    task_id: str
    status: Literal["pending", "running", "completed", "failed"]
    result: Optional[QuizGenerateResponse] = None
    error_message: str | None = None
