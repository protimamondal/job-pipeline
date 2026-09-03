from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "AI Job Pipeline API",
        "environment": "local",
    }
    assert response.headers["x-request-id"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
