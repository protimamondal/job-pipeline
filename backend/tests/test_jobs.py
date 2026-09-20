from fastapi.testclient import TestClient


def test_list_jobs(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/jobs", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    assert body[0]["company"] == "Northwind Labs"


def test_get_job(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/jobs/3", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Farrow & Vine"
    assert body["salary_usd"] is None


def test_get_job_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/jobs/999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_jobs_require_a_token(client: TestClient) -> None:
    assert client.get("/jobs").status_code == 401
    assert client.get("/jobs/1").status_code == 401
