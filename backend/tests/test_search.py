"""Search: the closest chunks first, and never another user's private chunks.

Vectors are made up and `embed` is faked, so nothing here calls OpenAI: only the direction of a
vector matters to cosine distance, which makes the expected order easy to see.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db_models import EMBEDDING_DIMENSIONS, Chunk, Document, User
from app.routers import search as search_router
from app.search import TOP_K, search_chunks
from tests.conftest import TestSessionLocal


def vector(x: float, y: float) -> list[float]:
    return [x, y] + [0.0] * (EMBEDDING_DIMENSIONS - 2)


def add_chunk(content: str, embedding: list[float], user_id: int | None = None) -> None:
    async def add() -> None:
        async with TestSessionLocal() as session:
            document = Document(
                doc_type="job" if user_id is None else "resume",
                user_id=user_id,
                title=content,
                content=content,
            )
            session.add(document)
            await session.flush()
            session.add(
                Chunk(
                    document_id=document.id,
                    user_id=user_id,
                    doc_type=document.doc_type,
                    chunk_index=0,
                    content=content,
                    embedding=embedding,
                )
            )
            await session.commit()

    asyncio.run(add())


def user_id_for(email: str) -> int:
    async def fetch() -> int:
        async with TestSessionLocal() as session:
            return await session.scalar(select(User.id).where(User.email == email))

    return asyncio.run(fetch())


def search(user_id: int, question_vector: list[float]) -> list[str]:
    async def run() -> list[str]:
        async with TestSessionLocal() as session:
            chunks = await search_chunks(session, user_id, question_vector)
            return [chunk.content for chunk in chunks]

    return asyncio.run(run())


def test_the_closest_chunk_comes_first(client: TestClient, register_user) -> None:
    register_user("protima@example.com")
    add_chunk("far", vector(0.0, 1.0))
    add_chunk("close", vector(1.0, 0.0))
    add_chunk("middle", vector(1.0, 1.0))

    results = search(user_id_for("protima@example.com"), vector(1.0, 0.0))

    assert results == ["close", "middle", "far"]


def test_at_most_top_k_chunks_come_back(client: TestClient, register_user) -> None:
    register_user("protima@example.com")
    for number in range(TOP_K + 2):
        add_chunk(f"job {number}", vector(1.0, 0.0))

    results = search(user_id_for("protima@example.com"), vector(1.0, 0.0))

    assert len(results) == TOP_K


def test_a_user_sees_public_chunks_and_their_own(
    client: TestClient, register_user
) -> None:
    register_user("protima@example.com")
    protima = user_id_for("protima@example.com")
    add_chunk("public job", vector(1.0, 0.0))
    add_chunk("my resume", vector(1.0, 0.0), user_id=protima)

    assert set(search(protima, vector(1.0, 0.0))) == {"public job", "my resume"}


def test_another_users_chunk_never_comes_back_even_when_it_is_the_closest(
    client: TestClient, register_user
) -> None:
    register_user("protima@example.com")
    register_user("rahul@example.com", name="Rahul")
    protima = user_id_for("protima@example.com")
    rahul = user_id_for("rahul@example.com")
    add_chunk("rahul's resume", vector(1.0, 0.0), user_id=rahul)
    add_chunk("public job", vector(0.0, 1.0))

    assert search(protima, vector(1.0, 0.0)) == ["public job"]


# POST /search: the endpoint. `embed` is replaced so no test calls OpenAI: the
# fake turns "react" into the vector (1, 0) and anything else into (0, 1).


@pytest.fixture
def fake_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def embed(client, texts: list[str]) -> list[list[float]]:
        return [
            vector(1.0, 0.0) if "react" in text.lower() else vector(0.0, 1.0)
            for text in texts
        ]

    monkeypatch.setattr(search_router, "embed", embed)


def test_the_endpoint_returns_the_closest_chunks_as_search_results(
    client: TestClient, auth_headers: dict[str, str], fake_embed
) -> None:
    add_chunk("React job", vector(1.0, 0.0))
    add_chunk("Python job", vector(0.0, 1.0))

    response = client.post(
        "/search", json={"question": "Which jobs use React?"}, headers=auth_headers
    )

    assert response.status_code == 200
    results = response.json()
    assert [result["content"] for result in results] == ["React job", "Python job"]
    # Only the SearchResult fields: no embedding, no user_id.
    assert set(results[0]) == {"id", "job_id", "doc_type", "content"}


def test_a_second_user_never_sees_the_first_users_chunks(
    client: TestClient, register_user, fake_embed
) -> None:
    protima = register_user("protima@example.com")
    rahul = register_user("rahul@example.com", name="Rahul")
    add_chunk(
        "Protima's React resume", vector(1.0, 0.0), user_id_for("protima@example.com")
    )
    add_chunk("public job", vector(0.0, 1.0))

    def contents(headers: dict[str, str]) -> list[str]:
        response = client.post("/search", json={"question": "React"}, headers=headers)
        return [result["content"] for result in response.json()]

    assert contents(protima) == ["Protima's React resume", "public job"]
    assert contents(rahul) == ["public job"]


def test_a_blank_or_huge_question_is_rejected(
    client: TestClient, auth_headers: dict[str, str], fake_embed
) -> None:
    blank = client.post("/search", json={"question": "   "}, headers=auth_headers)
    huge = client.post("/search", json={"question": "x" * 1001}, headers=auth_headers)

    assert blank.status_code == 422
    assert huge.status_code == 422


def test_search_needs_a_login(client: TestClient, fake_embed) -> None:
    assert client.post("/search", json={"question": "React"}).status_code == 401
