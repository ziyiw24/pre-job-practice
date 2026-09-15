from fastapi.testclient import TestClient
from app.core.config import get_settings
from app.core.rate_limit import _events
from app.main import app

def test_login_rate_limit_has_stable_error_code():
    settings=get_settings(); old=settings.rate_limit_login; settings.rate_limit_login=1; _events.clear()
    try:
        with TestClient(app) as client:
            client.post("/api/v1/user/login",json={"code":"x"})
            response=client.post("/api/v1/user/login",json={"code":"x"})
        assert response.status_code==429 and response.json()["code"]==4290
    finally:settings.rate_limit_login=old;_events.clear()

def test_request_body_limit_returns_413_before_parsing():
    with TestClient(app) as client:response=client.post("/api/v1/training/generate/async",content=b"x",headers={"content-length":"99999999","content-type":"application/json"})
    assert response.status_code==413 and response.json()["code"]==4130
