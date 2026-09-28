from fastapi.testclient import TestClient


def test_chat_requires_a_token(client: TestClient) -> None:
    assert client.post("/chat", json={"messages": []}).status_code == 401
