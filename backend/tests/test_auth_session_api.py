from fastapi.testclient import TestClient

from app.main import app


def test_dev_login_builds_server_side_membership_and_session():
    with TestClient(app) as client:
        login=client.post("/api/v1/auth/dev-login",json={"role":"manager"}).json()
        assert login["code"]==0
        token=login["data"]["token"]
        session=client.get("/api/v1/auth/session",headers={"Authorization":f"Bearer {token}"}).json()["data"]
        assert session["active_membership"]["role"]=="manager"
        assert session["active_membership"]["store_id"]=="store_demo"


def test_dev_employee_sees_only_own_assignment_without_answers():
    with TestClient(app) as client:
        token=client.post("/api/v1/auth/dev-login",json={"role":"employee"}).json()["data"]["token"]
        headers={"Authorization":f"Bearer {token}"}
        assignments=client.get("/api/v1/employee/assignments",headers=headers).json()["data"]
        assert assignments[0]["id"]=="assignment_demo"
        questions=client.get("/api/v1/employee/assignments/assignment_demo/questions",headers=headers).json()["data"]
        assert "answer" not in questions[0] and "explanation" not in questions[0]


def test_manager_invites_employee_and_membership_is_server_side():
    with TestClient(app) as client:
        manager_token=client.post("/api/v1/auth/dev-login",json={"role":"manager"}).json()["data"]["token"]
        invite=client.post(
            "/api/v1/stores/store_demo/invites",
            headers={"Authorization":f"Bearer {manager_token}"},
            json={"role":"employee","max_uses":1,"expires_hours":24},
        ).json()["data"]["invite_code"]

        from app.core.auth import create_token
        employee_token=create_token(9010,"invite-test")
        headers={"Authorization":f"Bearer {employee_token}"}
        joined=client.post("/api/v1/stores/join",headers=headers,json={"invite_code":invite}).json()
        assert joined["data"]["role"]=="employee"
        session=client.get("/api/v1/auth/session",headers=headers).json()["data"]
        assert session["active_membership"]["store_id"]=="store_demo"
