from fastapi.testclient import TestClient
from app.core.auth import create_token
from app.main import app

def headers(user): return {"Authorization":f"Bearer {create_token(user,f'openid-{user}')}"}
QUESTION={"id":"q1","type":"single","stem":"应该如何操作？","options":[{"key":"A","text":"正确做法"},{"key":"B","text":"错误做法"}],"answer":["A"],"explanation":"应选A","knowledge_point":"操作","evidence":{"quote":"必须使用正确做法"},"requires_confirmation":False}

def test_employee_cannot_receive_answer_and_server_scores():
    with TestClient(app) as c:
        store=c.post("/api/v1/stores",json={"name":"A店"},headers=headers(1)).json()["data"]
        c.post(f"/api/v1/stores/{store['id']}/members",json={"user_id":2,"role":"employee"},headers=headers(1))
        course=c.post(f"/api/v1/stores/{store['id']}/courses",json={"title":"岗位课","questions":[QUESTION]},headers=headers(1)).json()["data"]
        c.post(f"/api/v1/courses/{course['id']}/publish",headers=headers(1))
        assignment=c.post(f"/api/v1/courses/{course['id']}/assignments",json={"employee_user_id":2},headers=headers(1)).json()["data"]
        questions=c.get(f"/api/v1/employee/assignments/{assignment['id']}/questions",headers=headers(2)).json()["data"]
        assert "answer" not in questions[0] and "explanation" not in questions[0]
        report=c.post(f"/api/v1/employee/assignments/{assignment['id']}/answers",json={"answers":[{"question_id":"q1","selected_answers":["A"],"duration_ms":5}]},headers=headers(2)).json()["data"]
        assert report["score"]==100
        assert c.get(f"/api/v1/employee/assignments/{assignment['id']}/questions",headers=headers(3)).json()["code"]==4030
        results=c.get(f"/api/v1/stores/{store['id']}/results",headers=headers(1)).json()["data"]
        assert results[0]["score"]==100
        assert c.get(f"/api/v1/stores/{store['id']}/results",headers=headers(3)).json()["code"]==4030
        assert c.get(f"/api/v1/stores/{store['id']}/dashboard",headers=headers(1)).json()["data"]["course_count"]==1
        assert c.get(f"/api/v1/stores/{store['id']}/courses",headers=headers(1)).json()["data"][0]["title"]=="岗位课"
        assert c.get(f"/api/v1/stores/{store['id']}/members",headers=headers(3)).json()["code"]==4030
        completed=c.get("/api/v1/employee/assignments?status=completed",headers=headers(2)).json()["data"]
        assert completed[0]["score"]==100
