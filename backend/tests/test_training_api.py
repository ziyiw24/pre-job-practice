"""上岗练 M0 核心链路测试。"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.training import TrainingGenerateRequest, TrainingReportRequest
from app.services import training_service


@pytest.fixture()
def manual_text():
    return training_service.DEMO_CONTENT


def test_demo_endpoint_does_not_require_login():
    with TestClient(app) as client:
        response = client.get("/api/v1/training/demo")
    body = response.json()
    assert body["code"] == 0
    assert len(body["data"]["content"]) >= 100


@pytest.mark.asyncio
async def test_generate_quiz_has_verbatim_evidence(monkeypatch, manual_text):
    monkeypatch.setattr(training_service, "is_chat_model_configured", lambda: False)
    request = TrainingGenerateRequest(
        client_request_id="request_evidence_001",
        title="原料培训",
        content=manual_text,
        question_count=3,
    )
    created = await training_service.create_training_task(request)
    for _ in range(10):
        task = await training_service.get_training_task(created.task_id)
        if task and task.status == "completed":
            break
        await asyncio.sleep(0.01)
    assert task is not None and task.result is not None
    assert task.result.ai_generated is False
    assert len(task.result.questions) == 3
    for question in task.result.questions:
        quote = question.evidence.quote
        assert quote in manual_text
        assert manual_text[question.evidence.start_offset:question.evidence.end_offset] == quote


@pytest.mark.asyncio
async def test_client_request_id_is_idempotent(monkeypatch, manual_text):
    monkeypatch.setattr(training_service, "is_chat_model_configured", lambda: False)
    request = TrainingGenerateRequest(
        client_request_id="request_idempotent_001",
        content=manual_text,
        question_count=3,
    )
    first = await training_service.create_training_task(request)
    second = await training_service.create_training_task(request)
    assert first.task_id == second.task_id


@pytest.mark.asyncio
async def test_report_score_is_computed_by_server(monkeypatch, manual_text):
    monkeypatch.setattr(training_service, "is_chat_model_configured", lambda: False)
    quiz = training_service._make_demo_quiz(TrainingGenerateRequest(
        client_request_id="request_score_001", content=manual_text, question_count=3,
    ))
    report = await training_service.generate_training_report(TrainingReportRequest(
        quiz_id=quiz.quiz_id,
        questions=quiz.questions,
        answer_records=[
            {"question_id": quiz.questions[0].id, "selected_answers": quiz.questions[0].answer, "duration_ms": 500},
            {"question_id": quiz.questions[1].id, "selected_answers": ["missing"], "duration_ms": 500},
            {"question_id": quiz.questions[2].id, "selected_answers": quiz.questions[2].answer, "duration_ms": 500},
        ],
    ))
    assert report.correct_count == 2
    assert report.score == 67
    assert report.result == "needs_review"
    assert report.ai_generated is False
