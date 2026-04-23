from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_observability_health_endpoint():
    client = TestClient(app)
    response = client.get("/observability/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
