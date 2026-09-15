from pydantic import BaseModel, Field

class HumanQuestionJudgment(BaseModel):
    case_id: str; question_id: str
    answer_unique: bool
    scenario_effective: bool
    manager_verdict: str = Field(pattern="^(usable|minor_edit|reject)$")
    note: str = ""
