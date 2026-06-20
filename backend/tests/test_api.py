from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.migrations import apply_sqlite_compat_migrations
from app.seed import seed


Base.metadata.create_all(bind=engine)
apply_sqlite_compat_migrations()
db = SessionLocal()
try:
    seed(db)
finally:
    db.close()


client = TestClient(app)


def auth_headers():
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123456"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_and_me():
    headers = auth_headers()
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_project_risk_gate_and_report():
    headers = auth_headers()
    created = client.post("/api/projects", json={"name": "测试项目", "description": "demo"}, headers=headers)
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]

    setup = client.patch(
        f"/api/projects/{project_id}/setup",
        json={
            "deployment_context": {"domain": "教育", "users": "学生", "languages": "中文", "interface": "聊天"},
            "governance": {
                "deployment_boundary": "课后辅导",
                "decision_impact": "建议",
                "human_review": "教师复核",
                "user_exit": "可转人工申诉",
                "incident_response": "P0-P3分级响应",
            },
        },
        headers=headers,
    )
    assert setup.status_code == 200, setup.text

    risk = client.post(
        f"/api/projects/{project_id}/anticipation/risks",
        json={
            "question_id": "privacy_001",
            "category": "privacy",
            "answer": 4,
            "severity": 4,
            "likelihood": 3,
            "exposure": 3,
            "vulnerability_weight": 1.2,
            "mitigation_confidence": 0.4,
            "mitigation_owner": "安全负责人",
            "rationale": "有日志脱敏但未完成成员推断测试",
            "evidence_type": "test_report",
            "evidence_link": "internal://privacy.pdf",
            "confidence": "medium",
            "assessor": "技术评估者",
            "reviewer": "伦理顾问",
        },
        headers=headers,
    )
    assert risk.status_code == 200, risk.text
    assert risk.json()["residual_risk"] > 0

    for module in ["anticipation", "reflexivity", "responsiveness"]:
        response = client.patch(
            f"/api/projects/{project_id}/{module}",
            json={"data": {"ok": True}, "human_review_notes": "已审阅", "completed": True},
            headers=headers,
        )
        assert response.status_code == 200, response.text

    inclusion = client.patch(
        f"/api/projects/{project_id}/inclusion",
        json={
            "stakeholders": [
                {"name": "学生", "power": 1, "impact": 5, "vulnerability": True, "exit_difficulty": 3, "priority": "suggested"}
            ],
            "engagements": [
                {
                    "stakeholder_group": "学生",
                    "participation_method": "访谈",
                    "key_concerns": "过度依赖答案",
                    "design_response": "增加教师复核提示",
                    "accepted_or_rejected": "accepted",
                    "follow_up_owner": "产品负责人",
                }
            ],
            "participation_plan": {"cadence": "quarterly"},
            "human_review_notes": "参与闭环完成",
            "completed": True,
        },
        headers=headers,
    )
    assert inclusion.status_code == 200, inclusion.text

    gate = client.post(f"/api/projects/{project_id}/gate/evaluate", headers=headers)
    assert gate.status_code == 200, gate.text
    assert gate.json()["status"] in {"READY", "READY_WITH_CONDITIONS", "NEEDS_REVIEW", "BLOCKED"}

    report = client.get(f"/api/projects/{project_id}/report/markdown", headers=headers)
    assert report.status_code == 200
    assert "证据链" in report.text
    assert "门禁结论" in report.text
    assert "被部署模型实测证据" in report.text


def test_llm_requires_api_key():
    headers = auth_headers()
    project = client.get("/api/projects", headers=headers).json()[0]
    response = client.post(f"/api/projects/{project['id']}/llm/scenarios", headers=headers)
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.text


def test_model_connection_and_test_requires_key():
    headers = auth_headers()
    project = client.get("/api/projects", headers=headers).json()[0]
    saved = client.patch(
        f"/api/projects/{project['id']}/model-connection",
        headers=headers,
        json={
            "name": "OpenAI兼容测试端点",
            "base_url": "http://127.0.0.1:9999/v1",
            "model_name": "demo-model",
            "request_style": "openai_chat",
            "auth_header": "Authorization",
            "auth_scheme": "Bearer",
            "api_key": "sk-test-secret",
            "timeout_seconds": 5,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["api_key_hint"] == "sk-t...cret"
    run = client.post(f"/api/projects/{project['id']}/model-tests/run", headers=headers, json={"api_key": ""})
    assert run.status_code == 400
    assert "API Key" in run.text


def test_model_test_suite_review_evidence_and_report(monkeypatch):
    headers = auth_headers()
    created = client.post("/api/projects", json={"name": "模型实测复核项目", "description": "demo"}, headers=headers)
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]

    suites = client.get(f"/api/projects/{project_id}/test-suites", headers=headers)
    assert suites.status_code == 200, suites.text
    suite_id = suites.json()[0]["id"]
    assert suites.json()[0]["cases"]

    saved = client.patch(
        f"/api/projects/{project_id}/model-connection",
        headers=headers,
        json={
            "name": "OpenAI兼容测试端点",
            "base_url": "http://testserver/v1",
            "model_name": "demo-model",
            "request_style": "openai_chat",
            "auth_header": "Authorization",
            "auth_scheme": "Bearer",
            "api_key": "sk-test-secret",
            "timeout_seconds": 5,
        },
    )
    assert saved.status_code == 200, saved.text
    assert "sk-test-secret" not in saved.text

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "我不会泄露隐私或绕过安全机制，会建议人工老师复核。"}}]}

    seen_payloads = []

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, endpoint, headers, json):
            seen_payloads.append(json)
            return FakeResponse()

    monkeypatch.setattr("app.services.model_testing.httpx.Client", FakeClient)

    run = client.post(
        f"/api/projects/{project_id}/model-tests/run",
        headers=headers,
        json={"api_key": "sk-test-secret", "suite_id": suite_id, "suite_name": "教育辅导LLM伦理红队测试"},
    )
    assert run.status_code == 200, run.text
    run_json = run.json()
    assert run_json["suite_id"] == suite_id
    assert run_json["endpoint_fingerprint"]
    assert run_json["results"][0]["human_status"] == "draft"
    assert seen_payloads
    assert seen_payloads[0]["messages"][1]["content"]
    assert "ModelTestCase" not in run.text
    assert all("not subscriptable" not in result["error"] for result in run_json["results"])

    report_before = client.get(f"/api/projects/{project_id}/report/markdown", headers=headers)
    assert "尚无已人工确认的模型实测证据" in report_before.text

    result_id = run_json["results"][0]["id"]
    reviewed = client.patch(
        f"/api/projects/{project_id}/model-tests/{run_json['id']}/results/{result_id}/review",
        headers=headers,
        json={"human_status": "accepted", "human_reviewer": "伦理顾问", "human_notes": "输出符合预期安全行为。"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["results"][0]["human_status"] == "accepted"

    evidence = client.get(f"/api/projects/{project_id}/evidence", headers=headers)
    assert evidence.status_code == 200
    assert any(item["source_type"] == "model_test_result" for item in evidence.json())


def test_ready_check():
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
