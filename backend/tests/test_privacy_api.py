from fastapi.testclient import TestClient
from app.core.auth import create_token
from app.main import app

def test_privacy_request_requires_login_and_returns_tracking_id():
    with TestClient(app) as client:
        assert client.post("/api/v1/privacy/requests",json={"request_type":"complaint","detail":"x"}).status_code==401
        token=create_token(88,"privacy-user");body=client.post("/api/v1/privacy/requests",json={"request_type":"delete_account","detail":"请删除"},headers={"Authorization":f"Bearer {token}"}).json()
    assert body["code"]==0 and body["data"]["status"]=="pending"
