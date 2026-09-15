from typing import Literal
from pydantic import BaseModel, Field


class DocumentBlock(BaseModel):
    block_id: str
    page_number: int | None = None
    paragraph_index: int
    text: str
    start_offset: int
    end_offset: int


class TrainingDocument(BaseModel):
    document_id: str
    file_name: str
    status: Literal["uploaded", "parsing", "ready", "failed"]
    blocks: list[DocumentBlock] = Field(default_factory=list)
    content: str = ""
    error_code: str | None = None
    error_message: str | None = None
    storage_key: str | None = None
    store_id: str | None = None
    owner_user_id: int | None = None
    deleted: bool = False


class DraftQuestionUpdate(BaseModel):
    stem: str | None = None
    options: list[dict] | None = None
    answer: list[str] | None = None
    explanation: str | None = None
    confirmed: bool | None = None


class TrainingDraft(BaseModel):
    quiz_id: str
    document_id: str
    status: Literal["draft", "awaiting_review", "approved", "published"] = "draft"
    questions: list[dict]
    confirmed_question_ids: list[str] = Field(default_factory=list)
    store_id: str | None = None


class DocumentGenerateRequest(BaseModel):
    title: str = Field(default="", max_length=60)
    question_count: Literal[3, 5] = 5
    difficulty: Literal["easy", "mixed", "hard"] = "mixed"
