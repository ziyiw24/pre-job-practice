"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import auth_session, health, knowledge, platform, privacy, quiz, report, topics, training, training_documents, user
from app.core.config import get_settings, validate_production_settings
from app.core.db import close_mysql_pool, connect_mysql, init_mysql
from app.core.exceptions import (
    AuthenticationError,
    ContentFilterError,
    KnowledgeBaseError,
    QuizGenerationError,
    ReportGenerationError,
)
from app.models.common import ApiResponse
from app.core.rate_limit import allow_request

logger = structlog.get_logger()


class RequestBodyTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    """同时检查声明大小与实际接收字节，覆盖 chunked/伪造 Content-Length。"""
    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        declared = headers.get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            response = JSONResponse(status_code=413, content=ApiResponse.error(4130, "请求内容超过大小限制").model_dump())
            return await response(scope, receive, send)
        received = 0
        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge
            return message
        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(status_code=413, content=ApiResponse.error(4130, "请求内容超过大小限制").model_dump())
            await response(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    validate_production_settings(settings)
    logger.info("app_starting", host=settings.app_host, port=settings.app_port)
    if settings.mysql_auto_init:
        await init_mysql()
    elif settings.mysql_connect_on_start:
        await connect_mysql()
    yield
    await close_mysql_pool()
    logger.info("app_shutting_down")



app = FastAPI(
    title="上岗练 API",
    description="将门店培训内容转换为有原文依据的练习与学习报告。",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=get_settings().max_request_body_bytes)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def enforce_request_size(request: Request, call_next):
    if not await allow_request(request):
        return JSONResponse(status_code=429, content=ApiResponse.error(4290, "请求过于频繁，请稍后再试").model_dump())
    return await call_next(request)

# 注册路由
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth_session.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(topics.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
app.include_router(training_documents.router, prefix="/api/v1")
app.include_router(training_documents.draft_router, prefix="/api/v1")
app.include_router(platform.router, prefix="/api/v1")
app.include_router(privacy.router, prefix="/api/v1")


# 全局异常处理
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content=ApiResponse.error(code=4010, message=str(exc)).model_dump(),
    )


@app.exception_handler(ContentFilterError)
async def content_filter_handler(request: Request, exc: ContentFilterError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4000, message=str(exc)).model_dump(),
    )


@app.exception_handler(QuizGenerationError)
async def quiz_error_handler(request: Request, exc: QuizGenerationError):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5001, message=str(exc)).model_dump(),
    )


@app.exception_handler(ReportGenerationError)
async def report_error_handler(request: Request, exc: ReportGenerationError):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5002, message=str(exc)).model_dump(),
    )


@app.exception_handler(KnowledgeBaseError)
async def knowledge_base_error_handler(request: Request, exc: KnowledgeBaseError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4001, message=str(exc)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底异常处理：避免直接暴露裸的 "Internal Server Error"，并记录完整堆栈便于排查。"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5000, message="服务器内部错误，请稍后重试").model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
