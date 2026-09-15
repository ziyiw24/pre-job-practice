"""精选专题路由。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.common import ApiResponse
from app.services.topic_service import get_topic, list_topics

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=ApiResponse)
async def topics_list(
    category: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=50),
):
    items = list_topics(category=category, difficulty=difficulty, keyword=keyword)
    return ApiResponse.success(data={"items": [item.model_dump() for item in items], "total": len(items)})


@router.get("/{topic_id}", response_model=ApiResponse)
async def topic_detail(topic_id: str):
    topic = get_topic(topic_id)
    if topic is None:
        return ApiResponse.error(code=4041, message="专题不存在或未通过审核")
    return ApiResponse.success(data=topic.model_dump())
