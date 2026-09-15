"""上岗练 M0 匿名核心流程接口。"""

from fastapi import APIRouter

from app.models.common import ApiResponse
from app.models.training import TrainingGenerateRequest, TrainingReportRequest
from app.services.training_service import (
    create_training_task,
    generate_training_report,
    get_demo,
    get_training_task,
)

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/generate/async", response_model=ApiResponse)
async def generate_async(req: TrainingGenerateRequest):
    result = await create_training_task(req)
    return ApiResponse.success(result.model_dump())


@router.get("/tasks/{task_id}", response_model=ApiResponse)
async def get_task(task_id: str):
    result = await get_training_task(task_id)
    if result is None:
        return ApiResponse.error(4040, "本次生成已过期或不存在，请重新生成")
    return ApiResponse.success(result.model_dump())


@router.post("/reports", response_model=ApiResponse)
async def create_report(req: TrainingReportRequest):
    result = await generate_training_report(req)
    return ApiResponse.success(result.model_dump())


@router.get("/demo", response_model=ApiResponse)
async def demo():
    return ApiResponse.success(get_demo().model_dump())
