from fastapi.testclient import TestClient

from app.main import app


def test_health_and_query():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post(
            "/api/v1/query",
            headers={"Authorization": "Bearer demo-token"},
            json={"question": "最近四个月毛利润趋势"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "succeeded"
        assert body["trace_id"]
        trace = client.get(
            f"/api/v1/traces/{body['trace_id']}",
            headers={"Authorization": "Bearer demo-token"},
        )
        assert trace.status_code == 200
        assert any(event["node"] == "sql_guard" for event in trace.json())


def test_async_analysis_task_is_accepted():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": "Bearer demo-token"},
            json={"question": "最近三个月利润为什么下降"},
        )
        assert response.status_code == 202
        assert response.json()["task_id"].startswith("task_")
