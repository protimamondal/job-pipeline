from fastapi.testclient import TestClient


def test_a_new_pipeline_is_empty(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/applications", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_track_a_job(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/applications", json={"job_id": 2}, headers=auth_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["job"]["id"] == 2
    assert body["job"]["company"] == "Cobalt Health"
    assert body["status"] == "saved"
    assert "user_id" not in body


def test_track_a_job_with_an_explicit_status(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/applications",
        json={"job_id": 2, "status": "interviewing", "notes": "Phone screen booked"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "interviewing"


def test_tracking_the_same_job_twice_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/applications", json={"job_id": 2}, headers=auth_headers)

    repeat = client.post("/applications", json={"job_id": 2}, headers=auth_headers)
    assert repeat.status_code == 409


def test_tracking_a_job_that_does_not_exist(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/applications", json={"job_id": 999}, headers=auth_headers
    )
    assert response.status_code == 404


def test_an_invalid_status_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/applications", json={"job_id": 2, "status": "banana"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_update_a_status(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post("/applications", json={"job_id": 2}, headers=auth_headers)
    application_id = created.json()["id"]

    response = client.patch(
        f"/applications/{application_id}",
        json={"status": "applied"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"


def test_a_partial_update_leaves_other_fields_alone(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        "/applications",
        json={"job_id": 2, "status": "interviewing", "notes": "Round one done"},
        headers=auth_headers,
    )
    application_id = created.json()["id"]

    response = client.patch(
        f"/applications/{application_id}",
        json={"notes": "Round two booked"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["notes"] == "Round two booked"
    assert body["status"] == "interviewing"


def test_delete_an_application(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post("/applications", json={"job_id": 2}, headers=auth_headers)
    application_id = created.json()["id"]

    assert (
        client.delete(
            f"/applications/{application_id}", headers=auth_headers
        ).status_code
        == 204
    )
    assert client.get("/applications", headers=auth_headers).json() == []


def test_applications_require_a_token(client: TestClient) -> None:
    assert client.get("/applications").status_code == 401
    assert client.post("/applications", json={"job_id": 2}).status_code == 401
    assert client.patch("/applications/1", json={"status": "applied"}).status_code == 401
    assert client.delete("/applications/1").status_code == 401


# ── the sub-phase 2 acceptance check ──────────────────────────────────────


def test_two_users_have_separate_pipelines(client: TestClient, register_user) -> None:
    protima = register_user("protima@example.com")
    rahul = register_user("rahul@example.com", name="Rahul")

    # Both track the same job, at different stages.
    a = client.post(
        "/applications",
        json={"job_id": 2, "status": "interviewing"},
        headers=protima,
    )
    b = client.post(
        "/applications", json={"job_id": 2, "status": "rejected"}, headers=rahul
    )
    assert a.status_code == 201
    assert b.status_code == 201

    protima_pipeline = client.get("/applications", headers=protima).json()
    rahul_pipeline = client.get("/applications", headers=rahul).json()

    assert len(protima_pipeline) == 1
    assert len(rahul_pipeline) == 1
    assert protima_pipeline[0]["status"] == "interviewing"
    assert rahul_pipeline[0]["status"] == "rejected"
    assert protima_pipeline[0]["id"] != rahul_pipeline[0]["id"]


def test_one_user_cannot_read_or_modify_another_users_application(
    client: TestClient, register_user
) -> None:
    protima = register_user("protima@example.com")
    rahul = register_user("rahul@example.com", name="Rahul")

    created = client.post("/applications", json={"job_id": 2}, headers=protima)
    protima_application_id = created.json()["id"]

    # Rahul cannot see it in his pipeline.
    assert client.get("/applications", headers=rahul).json() == []

    # Nor change it, nor delete it — and it is reported as missing, not
    # forbidden, so he cannot learn that the id exists.
    patched = client.patch(
        f"/applications/{protima_application_id}",
        json={"status": "rejected"},
        headers=rahul,
    )
    assert patched.status_code == 404

    deleted = client.delete(
        f"/applications/{protima_application_id}", headers=rahul
    )
    assert deleted.status_code == 404

    # Protima's record is untouched.
    still_there = client.get("/applications", headers=protima).json()
    assert len(still_there) == 1
    assert still_there[0]["status"] == "saved"
