"""Filling `chunks`: every piece of every document, with its owner and a vector.

OpenAI is faked: these tests check our own logic, not the model, and must not
cost money.
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import embed_chunks
from app.db_models import EMBEDDING_DIMENSIONS, Chunk, User
from app.embed_chunks import embed_documents
from build_documents import build_documents
from seed_data import JOBS
from tests.conftest import TestSessionLocal


class FakeEmbeddings:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.batches: list[list[str]] = []

    async def create(self, model: str, input: list[str]) -> SimpleNamespace:
        if self.fail:
            raise RuntimeError("OpenAI is down")
        self.batches.append(input)
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[float(len(text))] * EMBEDDING_DIMENSIONS)
                for text in input
            ]
        )


def fake_client(fail: bool = False) -> SimpleNamespace:
    return SimpleNamespace(embeddings=FakeEmbeddings(fail))


def run_build_documents() -> None:
    async def once() -> None:
        async with TestSessionLocal() as session:
            await build_documents(session)

    asyncio.run(once())


def run_embed(client: SimpleNamespace) -> int:
    async def once() -> int:
        async with TestSessionLocal() as session:
            return await embed_documents(session, client)

    return asyncio.run(once())


def all_chunks() -> list[Chunk]:
    async def fetch() -> list[Chunk]:
        async with TestSessionLocal() as session:
            return list((await session.scalars(select(Chunk))).all())

    return asyncio.run(fetch())


def test_every_document_gets_chunks_with_the_title_and_a_vector(
    client: TestClient,
) -> None:
    run_build_documents()

    count = run_embed(fake_client())

    chunks = all_chunks()
    assert count == len(chunks) >= len(JOBS)
    assert {chunk.job_id for chunk in chunks} == set(range(1, len(JOBS) + 1))
    assert all(len(chunk.embedding) == EMBEDDING_DIMENSIONS for chunk in chunks)
    first_title = f"{JOBS[0]['title']} at {JOBS[0]['company']}"
    assert any(chunk.content.startswith(f"{first_title}\n\n") for chunk in chunks)


def test_a_private_chunk_keeps_its_owner(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.put(
        "/me/resume", json={"resume": "13 years of React."}, headers=auth_headers
    )
    run_build_documents()

    run_embed(fake_client())

    async def owner_id() -> int:
        async with TestSessionLocal() as session:
            return await session.scalar(select(User.id))

    resume = [chunk for chunk in all_chunks() if chunk.doc_type == "resume"]
    assert [chunk.user_id for chunk in resume] == [asyncio.run(owner_id())]
    assert all(c.user_id is None for c in all_chunks() if c.doc_type == "job")


def test_chunks_are_sent_in_batches(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embed_chunks, "BATCH_SIZE", 3)
    run_build_documents()
    fake = fake_client()

    count = run_embed(fake)

    sizes = [len(batch) for batch in fake.embeddings.batches]
    assert sum(sizes) == count
    assert max(sizes) == 3


def test_a_second_run_replaces_the_chunks(client: TestClient) -> None:
    run_build_documents()

    first = run_embed(fake_client())
    second = run_embed(fake_client())

    assert first == second == len(all_chunks())


def test_a_failed_embedding_leaves_the_old_chunks(client: TestClient) -> None:
    run_build_documents()
    saved = run_embed(fake_client())

    with pytest.raises(RuntimeError):
        run_embed(fake_client(fail=True))

    assert len(all_chunks()) == saved
