from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_mysql_and_rabbitmq_ok() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"mysql": "ok", "rabbitmq": "ok"}}
