import pytest
from app.core.config import Settings, validate_production_settings
from app.main import RequestSizeLimitMiddleware

def test_production_rejects_insecure_defaults():
    with pytest.raises(RuntimeError):validate_production_settings(Settings(app_environment="production"))

def test_production_accepts_explicit_external_adapters():
    s=Settings(app_environment="production",jwt_secret="x"*32,cors_origins="https://admin.example.cn",training_task_store="redis",training_document_store="cos",platform_store="mysql",mysql_connect_on_start=True,cos_secret_id="id",cos_secret_key="key",cos_region="ap-shanghai",cos_bucket="private-bucket",demo_mode=True)
    validate_production_settings(s)


@pytest.mark.asyncio
async def test_request_size_checks_actual_stream_bytes():
    async def inner(scope, receive, send):
        await receive()
    middleware = RequestSizeLimitMiddleware(inner, max_bytes=3)
    incoming = iter([{"type":"http.request","body":b"1234","more_body":False}])
    sent = []
    async def receive(): return next(incoming)
    async def send(message): sent.append(message)
    await middleware({"type":"http","method":"POST","headers":[]}, receive, send)
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413
