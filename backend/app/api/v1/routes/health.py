"""健康检查路由"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.db import get_mysql_pool

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check():
    settings = get_settings()
    mysql_required = settings.mysql_auto_init or settings.mysql_connect_on_start or settings.platform_store == "mysql"
    checks = {"process": "ok", "mysql": "ok" if get_mysql_pool() is not None else ("unavailable" if mysql_required else "disabled")}
    if settings.training_task_store == "redis":
        try:
            from redis.asyncio import from_url
            client = from_url(settings.redis_url, decode_responses=True)
            checks["redis"] = "ok" if await client.ping() else "unavailable"
            await client.aclose()
        except Exception:
            checks["redis"] = "unavailable"
    else:
        checks["redis"] = "disabled"
    checks["document_store"] = "configured" if settings.training_document_store != "cos" or all(
        [settings.cos_secret_id, settings.cos_secret_key, settings.cos_region, settings.cos_bucket]
    ) else "unavailable"
    ready = all(value not in {"unavailable"} for value in checks.values())
    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    return payload if ready else JSONResponse(status_code=503, content=payload)
