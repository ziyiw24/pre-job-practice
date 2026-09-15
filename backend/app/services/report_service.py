"""报告服务"""

from typing import Optional

import structlog

from app.core.exceptions import ReportGenerationError
from app.llm.report_chain import generate_report
from app.models.report import ReportGenerateRequest, ReportGenerateResponse
from app.services.scoring_service import compute_score_summary
from app.repositories import quiz_repository, user_repository
from app.llm.langchain_factory import is_chat_model_configured
from app.models.report import ReportOutput

logger = structlog.get_logger()


def _build_local_report(req: ReportGenerateRequest, score_summary: dict) -> ReportOutput:
    records = {record.question_id: record for record in req.answer_records}
    mastered = [q.knowledge_point for q in req.questions if records.get(q.id) and records[q.id].is_correct]
    weak = [q.knowledge_point for q in req.questions if records.get(q.id) and not records[q.id].is_correct]
    mastered = list(dict.fromkeys(mastered))
    weak = list(dict.fromkeys(weak))
    accuracy = round(score_summary["accuracy"])
    return ReportOutput(
        accuracy=accuracy,
        mastered_points=mastered,
        weak_points=weak,
        three_line_summary=[
            f"你完成了「{req.topic}」的 {score_summary['total']} 道学习题。",
            f"本次答对 {score_summary['correct']} 题，掌握度为 {accuracy}%。",
            "回看错题解析和来源，比只记住选项更重要。",
        ],
        advice=(
            [f"优先复习：{point}" for point in weak[:3]]
            if weak else ["换一组题再次回忆，巩固已掌握的知识。"]
        ),
        share_quote=f"今天我把「{req.topic}」学得更明白了。",
    )


async def handle_report_generate(
    req: ReportGenerateRequest,
    user_id: Optional[int] = None,
) -> ReportGenerateResponse:
    score_summary = compute_score_summary(req.answer_records)

    try:
        if is_chat_model_configured():
            report_output = await generate_report(
                topic=req.topic,
                questions=req.questions,
                answer_records=req.answer_records,
                score_summary=score_summary,
            )
        else:
            report_output = _build_local_report(req, score_summary)
    except Exception as e:
        logger.error("report_generation_failed", error=str(e))
        raise ReportGenerationError(f"报告生成失败：{e}") from e

    # 有登录态时落库
    if user_id is not None:
        try:
            # 保存答题记录
            await quiz_repository.save_answer_record(
                quiz_id=req.quiz_id,
                user_id=user_id,
                records_json=[r.model_dump() for r in req.answer_records],
                total_questions=score_summary["total"],
                correct_count=score_summary["correct"],
                accuracy=score_summary["accuracy"],
            )
            # 保存报告
            await quiz_repository.save_report(
                quiz_id=req.quiz_id,
                user_id=user_id,
                report_json=report_output.model_dump(),
            )
            # 累加经验值：完成闯关 +10，每答对一题 +2
            xp_gain = 10 + score_summary["correct"] * 2
            await user_repository.add_user_xp(user_id, xp_gain)
        except Exception as e:
            logger.error("report_persist_failed", error=str(e))

    return ReportGenerateResponse(
        accuracy=report_output.accuracy,
        mastered_points=report_output.mastered_points,
        weak_points=report_output.weak_points,
        three_line_summary=report_output.three_line_summary,
        advice=report_output.advice,
        share_quote=report_output.share_quote,
    )
