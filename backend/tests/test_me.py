"""The user's own resume: saved as text, readable only by its owner."""

from fastapi.testclient import TestClient


def test_a_new_user_has_no_resume(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/me/resume", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"resume": None}


def test_save_and_read_back_a_resume(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    saved = client.put(
        "/me/resume", json={"resume": "  13 years of React.  "}, headers=auth_headers
    )

    assert saved.status_code == 200
    assert saved.json() == {"resume": "13 years of React."}
    assert client.get("/me/resume", headers=auth_headers).json() == saved.json()


def test_saving_again_replaces_the_resume(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.put("/me/resume", json={"resume": "First version"}, headers=auth_headers)
    client.put("/me/resume", json={"resume": "Second version"}, headers=auth_headers)

    response = client.get("/me/resume", headers=auth_headers)

    assert response.json() == {"resume": "Second version"}


def test_a_blank_or_huge_resume_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    blank = client.put("/me/resume", json={"resume": "   "}, headers=auth_headers)
    huge = client.put("/me/resume", json={"resume": "x" * 20_001}, headers=auth_headers)

    assert blank.status_code == 422
    assert huge.status_code == 422


def test_one_user_never_sees_another_users_resume(
    client: TestClient, register_user
) -> None:
    protima = register_user("protima@example.com")
    rahul = register_user("rahul@example.com", name="Rahul")

    client.put("/me/resume", json={"resume": "Protima's resume"}, headers=protima)

    assert client.get("/me/resume", headers=rahul).json() == {"resume": None}


def test_the_resume_needs_a_login(client: TestClient) -> None:
    assert client.get("/me/resume").status_code == 401
    assert client.put("/me/resume", json={"resume": "x"}).status_code == 401
