from app.core.security import assess_health_risk
import pytest

from app.models.quiz import QuizGenerateRequest
from app.services.quiz_service import handle_quiz_generate
from app.services.topic_service import build_topic_context, get_topic, list_topics, match_topic


def test_only_approved_topics_are_listed():
    topics = list_topics()
    assert len(topics) >= 7
    assert all(topic.review_status == "approved" for topic in topics)
    assert {topic.category for topic in topics} == {"fitness", "tcm", "safety"}


def test_topic_filters_and_context_sources():
    topics = list_topics(category="fitness", difficulty="easy", keyword="训练")
    assert topics
    context = build_topic_context(topics[0])
    assert "【已审核专题】" in context
    assert "【来源】" in context


def test_unknown_topic_is_not_available():
    assert get_topic("missing") is None


def test_health_guard_blocks_diagnosis_and_emergency():
    diagnosis = assess_health_risk("请帮我辨证并开方")
    emergency = assess_health_risk("运动后胸痛并呼吸困难")
    assert not diagnosis.allowed
    assert not emergency.allowed
    assert emergency.emergency


def test_health_guard_allows_education():
    assert assess_health_risk("学习力量训练的基础原则").allowed


def test_natural_language_matches_reviewed_tcm_topics():
    assert match_topic("我想学一下胆经这个知识点").id == "topic_gallbladder_meridian"
    assert match_topic("给我出几道艾灸的题").id == "topic_moxibustion"


@pytest.mark.asyncio
async def test_free_text_learning_flow_works_without_model_key():
    result = await handle_quiz_generate(
        QuizGenerateRequest(user_input="我想学一下胆经", question_count=5)
    )
    assert result.topic_id == "topic_gallbladder_meridian"
    assert result.domain == "tcm"
    assert len(result.questions) == 5
    assert all(question.source_refs for question in result.questions)
