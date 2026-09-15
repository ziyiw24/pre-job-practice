from typing import Literal
from pydantic import BaseModel, Field
from app.models.training import TrainingAnswerRecord, TrainingQuestion

Role = Literal["owner", "manager", "employee"]
class StoreCreate(BaseModel): name: str = Field(min_length=1, max_length=100)
class MemberCreate(BaseModel): user_id: int; role: Role
class CourseCreate(BaseModel): title: str; questions: list[TrainingQuestion]; confirmed_question_ids: list[str] = Field(default_factory=list)
class AssignmentCreate(BaseModel): employee_user_id: int
class AssignmentSubmit(BaseModel): answers: list[TrainingAnswerRecord]
