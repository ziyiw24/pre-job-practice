"""上岗练有界质检修订 LangGraph。"""
from __future__ import annotations
import time

from langgraph.graph import END, START, StateGraph
import structlog

from app.agents.training.schemas import CriticResult, QuestionSet, QuizPlan, RuleSet
from app.agents.training.state import TrainingAgentState
from app.agents.training.validator import validate_questions
from app.prompts.training.quiz_v1 import GENERATE, PLAN, SYSTEM
from app.prompts.training.review_v1 import REVIEW, REWRITE

SYSTEM_BOUNDARY = SYSTEM
logger = structlog.get_logger()


def build_training_graph(gateway, progress=None):
    async def mark(stage):
        if progress: await progress(stage)

    async def extract(state):
        await mark("extracting")
        out = await gateway.generate_structured(system_prompt=SYSTEM_BOUNDARY, user_prompt="提取规则", output_schema=RuleSet, context={"content": state["content"]})
        valid = [r.model_dump() for r in out.rules if r.evidence.quote in state["content"]]
        return {"extracted_rules": valid, "model_calls": state.get("model_calls", 0) + 1}

    async def plan(state):
        await mark("planning")
        if not state["extracted_rules"]: return {"status": "awaiting_review", "deterministic_issues": [{"question_id": "*", "code": "EVIDENCE_MISSING", "detail": "未提取到有效规则", "severity": "high"}]}
        out = await gateway.generate_structured(system_prompt=SYSTEM_BOUNDARY, user_prompt=PLAN, output_schema=QuizPlan, context={"rules": state["extracted_rules"], "question_count": state["question_count"], "difficulty": state["difficulty"]})
        return {"quiz_plan": [x.model_dump() for x in out.items], "model_calls": state.get("model_calls", 0) + 1}

    async def generate(state):
        await mark("generating")
        out = await gateway.generate_structured(system_prompt=SYSTEM_BOUNDARY, user_prompt=GENERATE, output_schema=QuestionSet, context={"rules": state["extracted_rules"], "plan": state["quiz_plan"]})
        return {"questions": [q.model_dump() for q in out.questions], "model_calls": state.get("model_calls", 0) + 1}

    async def validate(state):
        await mark("validating")
        return {"deterministic_issues": validate_questions(state["content"], state["questions"], state["question_count"])}

    async def review(state):
        await mark("reviewing")
        if state.get("deterministic_issues"): return {"critic_issues": []}
        out = await gateway.generate_structured(system_prompt=SYSTEM_BOUNDARY, user_prompt=REVIEW, output_schema=CriticResult, context={"rules": state["extracted_rules"], "questions": state["questions"]})
        return {"critic_issues": [issue.model_dump() for issue in out.issues], "model_calls": state.get("model_calls", 0) + 1}

    async def rewrite(state):
        await mark("rewriting")
        failed = {i["question_id"] for i in state.get("deterministic_issues", []) + state.get("critic_issues", [])}
        out = await gateway.generate_structured(system_prompt=SYSTEM_BOUNDARY, user_prompt=REWRITE, output_schema=QuestionSet, context={"rules": state["extracted_rules"], "plan": [p for p in state["quiz_plan"] if p["question_id"] in failed]})
        replacements = {q.id: q.model_dump() for q in out.questions}
        return {"questions": [replacements.get(q["id"], q) for q in state["questions"]], "revision_count": state.get("revision_count", 0) + 1, "model_calls": state.get("model_calls", 0) + 1}

    async def human(state):
        await mark("awaiting_review")
        return {"status": "awaiting_review"}

    async def finalize(state):
        return {"status": "completed"}

    def observed(name, node):
        async def run(state):
            started = time.monotonic()
            try:
                result = await node(state)
                issues = result.get("deterministic_issues", []) + result.get("critic_issues", [])
                logger.info("training_agent_node", task_id=state.get("task_id"), node=name,
                            duration_ms=round((time.monotonic()-started)*1000),
                            issue_codes=[item.get("code") for item in issues], status="ok")
                return result
            except Exception as exc:
                logger.warning("training_agent_node", task_id=state.get("task_id"), node=name,
                               duration_ms=round((time.monotonic()-started)*1000),
                               error_category=type(exc).__name__, status="failed")
                raise
        return run

    def after_plan(state): return "human" if state.get("status") == "awaiting_review" else "generate"
    def route(state):
        issues = state.get("deterministic_issues", []) + state.get("critic_issues", [])
        if not issues: return "finalize"
        if any(i.get("severity") == "high" for i in issues): return "human"
        if state.get("revision_count", 0) >= state.get("max_revisions", 2) or state.get("model_calls", 0) >= state.get("max_model_calls", 6): return "human"
        return "rewrite"

    graph = StateGraph(TrainingAgentState)
    for name, node in [("extract", extract), ("plan", plan), ("generate", generate), ("validate", validate), ("review", review), ("rewrite", rewrite), ("human", human), ("finalize", finalize)]: graph.add_node(name, observed(name, node))
    graph.add_edge(START, "extract"); graph.add_edge("extract", "plan")
    graph.add_conditional_edges("plan", after_plan, {"generate": "generate", "human": "human"})
    graph.add_edge("generate", "validate"); graph.add_edge("validate", "review")
    graph.add_conditional_edges("review", route, {"rewrite": "rewrite", "human": "human", "finalize": "finalize"})
    graph.add_edge("rewrite", "validate"); graph.add_edge("human", END); graph.add_edge("finalize", END)
    return graph.compile()
