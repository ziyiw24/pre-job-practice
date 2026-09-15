"""出题服务"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import structlog

from app.core.security import assess_health_risk, check_content
from app.core.exceptions import QuizGenerationError, ContentFilterError, KnowledgeBaseError
from app.llm.quiz_chain import generate_quiz
from app.llm.langchain_factory import is_chat_model_configured
from app.models.quiz import (
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizOutput,
    QuizTaskCreateResponse,
    QuizTaskStatusResponse,
)
from app.repositories import quiz_repository
from app.repositories import task_repository
from app.repositories import knowledge_repository
from app.services import rag_service
from app.services import image_service
from app.services.local_quiz_service import generate_local_quiz
from app.services.topic_service import build_topic_context, get_topic, match_topic
from app.models.topic import Topic

HEALTH_NOTICE = "内容仅供知识学习，不替代专业医疗意见。"

logger = structlog.get_logger()


async def _maybe_generate_images(
    quiz_output: QuizOutput,
    quiz_id: str,
    user_id: Optional[int],
    generate_images: bool,
) -> Optional[str]:
    """若请求开启了配图，尝试为题目生成配图并写回 question.image_url。

    生图失败绝不影响出题主流程：任何异常都会被捕获并记录日志，题目正常返回（不带图片）。
    """
    if not generate_images:
        return None

    try:
        image_map, notice = await image_service.generate_images_for_quiz(
            quiz_output.questions, user_id, quiz_id
        )
        for q in quiz_output.questions:
            if q.id in image_map:
                q.image_url = image_map[q.id]
        return notice
    except Exception as e:
        logger.error("quiz_image_generation_failed", quiz_id=quiz_id, error=str(e))
        return None


async def _validate_doc_id(req: QuizGenerateRequest, user_id: Optional[int]) -> None:
    """若请求指定了 doc_id，校验用户已登录且文档存在、归属正确且已就绪"""
    if req.doc_id is None:
        return

    if user_id is None:
        raise KnowledgeBaseError("使用知识库出题需要先登录")

    doc = await knowledge_repository.get_document(req.doc_id, user_id)
    if doc is None:
        raise KnowledgeBaseError("知识库文档不存在")

    if doc["status"] != "ready":
        raise KnowledgeBaseError(f"知识库文档尚未就绪（当前状态：{doc['status']}），请稍后重试")


def _resolve_topic(req: QuizGenerateRequest) -> Topic | None:
    if req.topic_id:
        topic = get_topic(req.topic_id)
    elif req.doc_id is None:
        topic = match_topic(req.user_input)
    else:
        topic = None
    if req.doc_id is None and topic is None:
        raise KnowledgeBaseError(
            "暂未找到对应的已审核专题。可试试：胆经、艾灸、力量训练、运动恢复或四季养生。"
        )
    return topic


async def _fetch_context(req: QuizGenerateRequest, user_id: Optional[int], topic: Topic | None) -> str:
    """仅从已审核专题或用户自有知识库获取参考资料。"""
    if req.doc_id is not None:
        return await rag_service.fetch_rag_context(req.user_input, user_id, req.doc_id)
    if topic:
        return build_topic_context(topic)
    raise KnowledgeBaseError("未找到可用的审核资料")


def _request_subject(req: QuizGenerateRequest, topic: Topic | None) -> str:
    if topic:
        return topic.title
    return req.user_input.strip()


def _enrich_quiz(quiz_output: QuizOutput, topic: Topic | None) -> tuple[str, list[str], str]:
    domain = topic.category if topic else "general"
    risk_level = topic.risk_level if topic else "medium"
    source_refs = [f"{source.publisher}·{source.title}" for source in topic.sources] if topic else ["用户自有知识库"]
    for question in quiz_output.questions:
        question.domain = domain
        question.risk_level = risk_level
        question.source_refs = source_refs
    return domain, source_refs, risk_level


async def handle_quiz_generate(
    req: QuizGenerateRequest,
    user_id: Optional[int] = None,
) -> QuizGenerateResponse:
    topic = _resolve_topic(req)
    subject = _request_subject(req, topic)
    if not check_content(subject) or not check_content(req.user_input):
        raise ContentFilterError("输入内容包含不当内容，请修改后重试")
    risk = assess_health_risk(req.user_input)
    if not risk.allowed:
        raise ContentFilterError(risk.message)

    # 若指定了知识库文档，先校验其归属与状态
    await _validate_doc_id(req, user_id)

    # 获取参考资料：指定 doc_id 时走知识库 RAG，否则走联网搜索
    search_context = await _fetch_context(req, user_id, topic)

    try:
        if topic is not None and not is_chat_model_configured():
            quiz_output = generate_local_quiz(topic, req.question_count, req.difficulty)
        else:
            quiz_output = await generate_quiz(
                user_input=subject,
                question_count=req.question_count,
                difficulty=req.difficulty,
                search_context=search_context,
            )
    except Exception as e:
        logger.error("quiz_generation_failed", error=str(e))
        raise QuizGenerationError(f"题库生成失败：{e}") from e

    domain, source_refs, _ = _enrich_quiz(quiz_output, topic)
    quiz_id = f"quiz_{uuid.uuid4().hex[:12]}"

    # 按需为题目生成配图（不影响出题主流程）
    image_notice = await _maybe_generate_images(quiz_output, quiz_id, user_id, req.generate_images)

    # 有登录态时落库
    if user_id is not None:
        try:
            await quiz_repository.save_quiz_session(
                quiz_id=quiz_id,
                user_id=user_id,
                title=quiz_output.title,
                summary=quiz_output.summary,
                user_input=subject,
                questions_json=[q.model_dump() for q in quiz_output.questions],
            )
        except Exception as e:
            logger.error("quiz_session_save_failed", error=str(e))

    return QuizGenerateResponse(
        quiz_id=quiz_id,
        title=quiz_output.title,
        summary=quiz_output.summary,
        questions=quiz_output.questions,
        topic_id=topic.id if topic else req.topic_id,
        domain=domain,
        source_refs=source_refs,
        health_notice=HEALTH_NOTICE,
        image_notice=image_notice,
    )


# ---- 异步任务模式 ----

async def create_quiz_task(
    req: QuizGenerateRequest,
    user_id: Optional[int] = None,
) -> QuizTaskCreateResponse:
    """创建异步出题任务，立即返回 task_id"""
    topic = _resolve_topic(req)
    subject = _request_subject(req, topic)
    if not check_content(subject) or not check_content(req.user_input):
        raise ContentFilterError("输入内容包含不当内容，请修改后重试")
    risk = assess_health_risk(req.user_input)
    if not risk.allowed:
        raise ContentFilterError(risk.message)

    # 若指定了知识库文档，先校验其归属与状态；校验失败不进入后台任务
    await _validate_doc_id(req, user_id)

    task_id = f"task_{uuid.uuid4().hex[:12]}"

    await task_repository.create_task(
        task_id=task_id,
        user_id=user_id,
        user_input=subject,
        question_count=req.question_count,
        difficulty=req.difficulty,
    )

    # 在后台启动生成任务
    asyncio.create_task(_run_quiz_task(task_id, req, user_id, topic))

    return QuizTaskCreateResponse(task_id=task_id)


async def _run_quiz_task(
    task_id: str,
    req: QuizGenerateRequest,
    user_id: Optional[int],
    topic: Topic | None,
) -> None:
    """后台执行出题任务"""
    try:
        await task_repository.update_task_status(task_id, "running")
        logger.info("quiz_task_started", task_id=task_id)

        # 获取参考资料：指定 doc_id 时走知识库 RAG，否则走联网搜索
        search_context = await _fetch_context(req, user_id, topic)
        subject = _request_subject(req, topic)

        # 生成题目
        if topic is not None and not is_chat_model_configured():
            quiz_output = generate_local_quiz(topic, req.question_count, req.difficulty)
        else:
            quiz_output = await generate_quiz(
                user_input=subject,
                question_count=req.question_count,
                difficulty=req.difficulty,
                search_context=search_context,
            )

        domain, source_refs, _ = _enrich_quiz(quiz_output, topic)
        quiz_id = f"quiz_{uuid.uuid4().hex[:12]}"

        # 按需为题目生成配图（不影响出题主流程）
        image_notice = await _maybe_generate_images(quiz_output, quiz_id, user_id, req.generate_images)

        # 有登录态时落库
        if user_id is not None:
            try:
                await quiz_repository.save_quiz_session(
                    quiz_id=quiz_id,
                    user_id=user_id,
                    title=quiz_output.title,
                    summary=quiz_output.summary,
                    user_input=subject,
                    questions_json=[q.model_dump() for q in quiz_output.questions],
                )
            except Exception as e:
                logger.error("quiz_session_save_failed", task_id=task_id, error=str(e))

        result = QuizGenerateResponse(
            quiz_id=quiz_id,
            title=quiz_output.title,
            summary=quiz_output.summary,
            questions=quiz_output.questions,
            topic_id=topic.id if topic else req.topic_id,
            domain=domain,
            source_refs=source_refs,
            health_notice=HEALTH_NOTICE,
            image_notice=image_notice,
        )

        await task_repository.update_task_status(
            task_id, "completed", result_json=result.model_dump()
        )
        logger.info("quiz_task_completed", task_id=task_id, quiz_id=quiz_id)

    except Exception as e:
        logger.error("quiz_task_failed", task_id=task_id, error=str(e))
        await task_repository.update_task_status(
            task_id, "failed", error_message=str(e)[:500]
        )


async def get_quiz_task_status(task_id: str) -> QuizTaskStatusResponse:
    """查询任务状态"""
    row = await task_repository.get_task(task_id)
    if row is None:
        raise QuizGenerationError("任务不存在")

    result = None
    if row["status"] == "completed" and row.get("result_json"):
        result = QuizGenerateResponse.model_validate(row["result_json"])

    return QuizTaskStatusResponse(
        task_id=row["task_id"],
        status=row["status"],
        result=result,
        error_message=row.get("error_message"),
    )
