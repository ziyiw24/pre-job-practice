"""上岗练 M0 核心用例。"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
import uuid

import structlog

from app.llm.langchain_factory import is_chat_model_configured  # 兼容旧调用方；新流程使用统一网关配置
from app.models.training import (
    Evidence,
    TrainingDemoResponse,
    TrainingAgentInfo,
    TrainingGenerateRequest,
    TrainingOption,
    TrainingQuestion,
    TrainingQuiz,
    TrainingReport,
    TrainingReportRequest,
    TrainingTaskCreateResponse,
    TrainingTaskStatusResponse,
)
from app.repositories.training_task_store import TrainingTask, get_training_task_store

logger = structlog.get_logger()
_background_tasks: set[asyncio.Task] = set()

DEMO_TITLE = "原料时效与异常处理"
DEMO_CONTENT = """开店前，员工必须检查冷藏设备、洗手池和消毒用品是否正常。所有已开封的原料必须贴上标签，标签需写明开封时间、失效时间和操作人。未标记或标记不清的原料不得继续使用，应放入待处理区并报告当班负责人。
制作饮品前必须按照规范洗手，接触现金、垃圾或手机后需重新洗手。不得用同一把工具直接处理生熟不同物料。如发现原料有异味、变色、包装鼓胀或疑似污染，必须立即停止使用，隔离该原料并通知店长，不得自行尝味判断。
出品前，员工需核对杯型、糖度、温度要求和顾客备注。发现错做时不得直接修改标签后出杯，应按门店异常品处理流程重新制作并记录。顾客反馈饮品口感或温度异常时，员工应先停止交付，核对订单与制作记录，再按当班负责人确认的方案处理，不得与顾客争辩或擅自承诺超出权限的补偿。
每班结束前需清点高频原料和包材，如实记录实际数量；发现账实不符时应保留现场记录并向当班负责人说明，不得为了对平数据自行修改盘点结果。设备清洁完成后，操作人需检查零件是否安装到位、电源是否处于规定状态，并在清洁记录上签字。
交班时，交班人员必须说明待处理原料、设备异常和未完成事项，接班人员核对后才可签字确认。如果异常事项可能影响食品安全或设备正常运行，必须同时在交接记录中写明当前状态和已采取的措施，在负责人确认前不得恢复相关操作。""".strip()


def get_demo() -> TrainingDemoResponse:
    return TrainingDemoResponse(title=DEMO_TITLE, content=DEMO_CONTENT)


def _sentences(content: str) -> list[str]:
    chunks = re.split(r"[\n。！；;]+", content)
    cleaned = [chunk.strip("，, ") for chunk in chunks if 12 <= len(chunk.strip()) <= 180]
    important = [
        item for item in cleaned
        if re.search(r"必须|不得|严禁|应当|应|需要|需|立即|才可|如发现|发现", item)
    ]
    source = important or cleaned
    deduped: list[str] = []
    for item in source:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _risk_tags(text: str) -> list[str]:
    tags: list[str] = []
    checks = [
        ("number", r"\d"), ("temperature", r"温度|℃|度"),
        ("duration", r"时间|小时|分钟|时效|失效"), ("recipe", r"配方|糖度|杯型"),
        ("safety", r"安全|消毒|污染|异味|变色|鼓胀|隔离"),
        ("punishment", r"处罚|扣款|责任"), ("emergency", r"立即|火灾|漏电|烫伤"),
    ]
    for tag, pattern in checks:
        if re.search(pattern, text):
            tags.append(tag)
    return tags


def _make_demo_quiz(req: TrainingGenerateRequest) -> TrainingQuiz:
    rules = _sentences(req.content)
    if not rules:
        raise ValueError("未识别到可考核的规则，请粘贴更完整的培训内容")
    while len(rules) < req.question_count:
        rules += rules
    questions: list[TrainingQuestion] = []
    distractors = ["先继续操作，交班时再统一处理", "由员工根据经验自行决定", "只要顾客没有提出异议就可以忽略"]
    answer_slots = ["A", "B", "C", "D", "B"]
    for index, quote in enumerate(rules[: req.question_count]):
        correct_key = answer_slots[index % len(answer_slots)]
        options: list[TrainingOption] = []
        wrong_index = 0
        for key in ["A", "B", "C", "D"]:
            if key == correct_key:
                options.append(TrainingOption(key=key, text=quote))
            else:
                options.append(TrainingOption(key=key, text=distractors[wrong_index]))
                wrong_index += 1
        start = req.content.find(quote)
        tags = _risk_tags(quote)
        questions.append(TrainingQuestion(
            id=f"q{index + 1}", type="single", scenario="你在当班中遇到了手册描述的情况。",
            stem="根据培训内容，下列哪一项是正确做法？", options=options,
            answer=[correct_key], explanation=f"原文明确要求：{quote}。", knowledge_point=quote[:18],
            evidence=Evidence(quote=quote, start_offset=start, end_offset=start + len(quote)),
            risk_tags=tags, requires_confirmation=bool(tags),
        ))
    return TrainingQuiz(
        quiz_id=f"quiz_{uuid.uuid4().hex[:12]}", title=req.title.strip() or "门店培训练习",
        summary="根据你粘贴的内容提取的关键操作规则。", questions=questions,
        ai_generated=False, generation_mode="demo",
    )


def _validate_ai_quiz(data: dict, req: TrainingGenerateRequest) -> TrainingQuiz:
    raw_questions = data.get("questions") or []
    if len(raw_questions) != req.question_count:
        raise ValueError("模型返回的题目数量不符合要求")
    questions: list[TrainingQuestion] = []
    for index, raw in enumerate(raw_questions):
        raw["id"] = f"q{index + 1}"
        quote = str((raw.get("evidence") or {}).get("quote") or "").strip()
        start = req.content.find(quote)
        if start < 0:
            raise ValueError("题目的原文依据无法在输入中找到")
        raw["evidence"] = {"quote": quote, "start_offset": start, "end_offset": start + len(quote)}
        detected = _risk_tags(" ".join([quote, raw.get("stem", ""), raw.get("explanation", "")]))
        raw["risk_tags"] = sorted(set(raw.get("risk_tags", []) + detected))
        if raw["risk_tags"]:
            raw["requires_confirmation"] = True
        questions.append(TrainingQuestion.model_validate(raw))
    return TrainingQuiz(
        quiz_id=f"quiz_{uuid.uuid4().hex[:12]}", title=str(data.get("title") or req.title or "门店培训练习")[:60],
        summary=str(data.get("summary") or "根据培训内容生成的练习。")[:200],
        questions=questions, ai_generated=True, generation_mode="ai",
    )


async def _run_generation(task_id: str, req: TrainingGenerateRequest) -> None:
    task_store = get_training_task_store()
    started = time.monotonic()
    logger.info("training_agent_started", task_id=task_id, input_length=len(req.content), content_hash=hashlib.sha256(req.content.encode()).hexdigest(), graph_version="training-author-v1", prompt_version="training-v1")
    try:
        from app.agents.training.graph import build_training_graph
        from app.core.config import get_settings
        from app.infrastructure.llm.mock_training_gateway import MockTrainingModelGateway
        from app.infrastructure.llm.openai_compatible_gateway import OpenAICompatibleGateway
        settings = get_settings()
        gateway = MockTrainingModelGateway() if settings.demo_mode or settings.model_provider == "mock" else OpenAICompatibleGateway(settings)
        async def progress(stage: str):
            await task_store.update(task_id, status="running", progress_stage=stage)
        state = await asyncio.wait_for(build_training_graph(gateway, progress).ainvoke({
            "task_id": task_id, "title": req.title, "content": req.content,
            "question_count": req.question_count, "difficulty": req.difficulty,
            "revision_count": 0, "max_revisions": settings.training_max_revisions,
            "model_calls": 0, "max_model_calls": settings.training_max_model_calls,
            "status": "running", "prompt_version": "training-v1", "graph_version": "training-author-v1",
        }), timeout=settings.training_task_timeout_seconds)
        issues = state.get("deterministic_issues", []) + state.get("critic_issues", [])
        agent = TrainingAgentInfo(revision_count=state.get("revision_count", 0), max_revisions=settings.training_max_revisions,
            issue_count=len(issues), model_calls=state.get("model_calls", 0))
        if state.get("status") == "awaiting_review":
            await task_store.update(task_id, status="awaiting_review", progress_stage="awaiting_review", agent=agent)
            return
        data = {"title": req.title or "门店培训练习", "summary": "根据原文规则生成并通过自动证据校验。", "questions": state["questions"]}
        quiz = _validate_ai_quiz(data, req)
        quiz.ai_generated = not isinstance(gateway, MockTrainingModelGateway)
        quiz.generation_mode = "ai" if quiz.ai_generated else "demo"
        await task_store.update(task_id, status="completed", result=quiz, agent=agent)
        logger.info("training_agent_completed", task_id=task_id, duration_ms=round((time.monotonic()-started)*1000), model_calls=agent.model_calls, revision_count=agent.revision_count, issue_count=agent.issue_count)
    except Exception as exc:
        logger.warning("training_generation_failed", task_id=task_id, error_type=type(exc).__name__)
        await task_store.update(
            task_id, status="failed", error_code="MODEL_TIMEOUT" if isinstance(exc, asyncio.TimeoutError) else getattr(exc, "code", "OUTPUT_INVALID"),
            error_message="题目生成或校验失败，请检查培训内容后重试。",
        )


async def create_training_task(req: TrainingGenerateRequest) -> TrainingTaskCreateResponse:
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    task, created = await get_training_task_store().create_or_get(task_id, req.client_request_id)
    if created:
        background = asyncio.create_task(_run_generation(task.task_id, req))
        _background_tasks.add(background)
        background.add_done_callback(_background_tasks.discard)
    return TrainingTaskCreateResponse(task_id=task.task_id, status=task.status)


def _task_response(task: TrainingTask) -> TrainingTaskStatusResponse:
    return TrainingTaskStatusResponse(
        task_id=task.task_id, status=task.status, progress_stage=task.progress_stage,
        result=task.result, error_code=task.error_code, error_message=task.error_message, agent=task.agent,
    )


async def get_training_task(task_id: str) -> TrainingTaskStatusResponse | None:
    task = await get_training_task_store().get(task_id)
    return _task_response(task) if task else None


def _score(req: TrainingReportRequest) -> tuple[int, dict[str, bool], list[str], list[str]]:
    answers = {item.question_id: set(item.selected_answers) for item in req.answer_records}
    results = {q.id: answers.get(q.id, set()) == set(q.answer) for q in req.questions}
    mastered = list(dict.fromkeys(q.knowledge_point for q in req.questions if results[q.id]))
    weak = list(dict.fromkeys(q.knowledge_point for q in req.questions if not results[q.id]))
    score = round(sum(results.values()) * 100 / len(req.questions)) if req.questions else 0
    return score, results, mastered, weak


async def generate_training_report(req: TrainingReportRequest) -> TrainingReport:
    score, answer_results, mastered, weak = _score(req)
    correct_count = sum(answer_results.values())
    actions = [f"重新阅读「{point}」的原文规则，再做一次情景判断。" for point in weak[:3]]
    if not actions:
        actions = ["结合真实班次再复述一遍关键流程。"]
    summary = f"本次共 {len(req.questions)} 题，答对 {correct_count} 题，得分 {score}。"
    ai_generated = False
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.demo_mode and settings.model_provider != "mock":
        try:
            from app.agents.training.schemas import TrainingReportSuggestion
            from app.infrastructure.llm.openai_compatible_gateway import OpenAICompatibleGateway
            from app.prompts.training.report_v1 import SYSTEM
            ai = await OpenAICompatibleGateway(settings).generate_structured(
                system_prompt=SYSTEM, user_prompt="请基于程序计算结果生成简洁复训建议。",
                output_schema=TrainingReportSuggestion, temperature=0.2,
                context={
                "score": score, "correct_count": correct_count, "total_count": len(req.questions),
                "mastered_points": mastered, "weak_points": weak,
            })
            summary = ai.ai_summary[:400]
            proposed_actions = [item[:120] for item in ai.review_actions if item.strip()]
            if proposed_actions:
                actions = proposed_actions[:3]
            ai_generated = True
        except Exception as exc:
            logger.warning("training_report_ai_fallback", error_type=type(exc).__name__)
    return TrainingReport(
        score=score, correct_count=correct_count, total_count=len(req.questions),
        result="passed" if score >= 80 else "needs_review", mastered_points=mastered,
        weak_points=weak, review_actions=actions, ai_summary=summary,
        ai_generated=ai_generated, answer_results=answer_results,
    )
