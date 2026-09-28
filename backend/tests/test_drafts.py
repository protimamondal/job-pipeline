from fastapi.testclient import TestClient


def test_draft_requires_a_token(client: TestClient) -> None:
    assert client.post("/jobs/1/draft", json={"instruction": None}).status_code == 401
