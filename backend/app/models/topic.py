"""知衡精选专题模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    title: str
    publisher: str
    url: str = ""


class Topic(BaseModel):
    id: str
    slug: str
    title: str
    summary: str
    category: Literal["fitness", "tcm", "safety"]
    difficulty: Literal["easy", "medium", "hard"]
    review_status: Literal["approved", "draft", "archived"]
    updated_at: str
    risk_level: Literal["low", "medium", "high"]
    icon: str = "🌿"
    content: str = Field(exclude=True, default="")
    search_terms: list[str] = Field(exclude=True, default_factory=list)
    sources: list[SourceRef]


class TopicListResponse(BaseModel):
    items: list[Topic]
    total: int
