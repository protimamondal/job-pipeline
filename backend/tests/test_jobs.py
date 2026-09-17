from fastapi.testclient import TestClient


def test_list_jobs(client: TestClient) -> None:
    response = client.get("/jobs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    assert body[0]["company"] == "Northwind Labs"


def test_get_job(client: TestClient) -> None:
    response = client.get("/jobs/3")

    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Farrow & Vine"
    assert body["salary_usd"] is None


def test_get_job_not_found(client: TestClient) -> None:
    response = client.get("/jobs/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
