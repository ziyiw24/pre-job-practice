from typing import Literal
from pydantic import BaseModel, Field
from app.models.training import TrainingAnswerRecord, TrainingQuestion

Role = Literal["owner", "manager", "employee"]
class StoreCreate(BaseModel): name: str = Field(min_length=1, max_length=100)
class MemberCreate(BaseModel): user_id: int; role: Role
class CourseCreate(BaseModel): title: str; questions: list[TrainingQuestion]; confirmed_question_ids: list[str] = Field(default_factory=list)
class AssignmentCreate(BaseModel): employee_user_id: int
class AssignmentSubmit(BaseModel): answers: list[TrainingAnswerRecord]

class DevLoginRequest(BaseModel):
    role: Literal["manager", "employee"]
class InviteCreate(BaseModel):
    role: Literal["manager","employee"] = "employee"
    max_uses: int = Field(default=20,ge=1,le=500)
    expires_hours: int = Field(default=168,ge=1,le=720)
class InviteJoin(BaseModel): invite_code: str = Field(min_length=6,max_length=32)
