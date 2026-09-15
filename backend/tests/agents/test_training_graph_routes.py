import pytest
from app.agents.training.graph import build_training_graph
from app.infrastructure.llm.openai_compatible_gateway import FakeModelGateway

CONTENT=("员工必须在开店前检查设备并在记录表上签字。")*20
RULE={"rule_id":"r1","category":"procedure","statement":"员工必须在开店前检查设备并在记录表上签字","evidence":{"quote":"员工必须在开店前检查设备并在记录表上签字"},"risk_tags":[],"priority":"must"}
PLAN={"question_id":"q1","rule_id":"r1","scenario":"开店前","difficulty":"mixed"}
def q(quote=RULE["evidence"]["quote"]):return {"id":"q1","type":"single","stem":"哪项正确？","options":[{"key":"A","text":"检查并签字"},{"key":"B","text":"直接开工"}],"answer":["A"],"explanation":"根据原文","knowledge_point":"开店检查","evidence":{"quote":quote}}
def initial():return {"task_id":"t","title":"x","content":CONTENT,"question_count":1,"difficulty":"mixed","revision_count":0,"max_revisions":2,"model_calls":0,"max_model_calls":6,"status":"running","prompt_version":"v1","graph_version":"v1"}

@pytest.mark.asyncio
async def test_medium_critic_issue_rewrites_only_failed_question():
    gateway=FakeModelGateway([{"rules":[RULE]},{"items":[PLAN]},{"questions":[q()]},{"issues":[{"question_id":"q1","code":"ANSWER_AMBIGUOUS","detail":"x","severity":"medium"}]},{"questions":[q()]},{"issues":[]}])
    out=await build_training_graph(gateway).ainvoke(initial())
    assert out["status"]=="completed" and out["revision_count"]==1 and out["model_calls"]==6

@pytest.mark.asyncio
async def test_high_deterministic_issue_routes_to_human_without_critic_override():
    invalid=q();invalid["stem"]="必须等待 99 分钟吗？"
    gateway=FakeModelGateway([{"rules":[RULE]},{"items":[PLAN]},{"questions":[invalid]}])
    out=await build_training_graph(gateway).ainvoke(initial())
    assert out["status"]=="awaiting_review" and out["model_calls"]==3

@pytest.mark.asyncio
async def test_missing_evidence_rewrites_failed_question():
    gateway=FakeModelGateway([{"rules":[RULE]},{"items":[PLAN]},{"questions":[q("不在原文中的证据")]},{"questions":[q()]},{"issues":[]}])
    out=await build_training_graph(gateway).ainvoke(initial())
    assert out["status"]=="completed" and out["revision_count"]==1
