from fastapi.testclient import TestClient


def test_register_returns_the_user_without_any_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"name": "Protima", "email": "p@example.com", "password": "devpassword"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "p@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_rejects_a_duplicate_email(client: TestClient) -> None:
    payload = {"name": "Protima", "email": "p@example.com", "password": "devpassword"}
    assert client.post("/auth/register", json=payload).status_code == 201

    repeat = client.post("/auth/register", json=payload)
    assert repeat.status_code == 409


def test_register_rejects_a_malformed_email(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"name": "x", "email": "not-an-email", "password": "devpassword"},
    )
    assert response.status_code == 422


def test_login_returns_a_token(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"name": "Protima", "email": "p@example.com", "password": "devpassword"},
    )

    response = client.post(
        "/auth/login", json={"email": "p@example.com", "password": "devpassword"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_a_wrong_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"name": "Protima", "email": "p@example.com", "password": "devpassword"},
    )

    response = client.post(
        "/auth/login", json={"email": "p@example.com", "password": "wrong"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_login_rejects_an_unknown_email_identically(client: TestClient) -> None:
    """A wrong password and an unregistered email must be indistinguishable."""
    response = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "devpassword"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_me_returns_the_logged_in_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == "protima@example.com"


def test_me_rejects_a_missing_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client: TestClient) -> None:
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert response.status_code == 401
