"""Rebuilding `documents`, the table RAG reads: every job, and each user's own text.

The property that matters most is privacy: a resume or a note is written with
its owner's `user_id`, because from Part 4 every retrieval query filters on it.
"""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db_models import Document, Job, User
from build_documents import build_documents
from seed_data import JOBS
from tests.conftest import TestSessionLocal


def run_build() -> dict[str, int]:
    async def once() -> dict[str, int]:
        async with TestSessionLocal() as session:
            return await build_documents(session)

    return asyncio.run(once())


def all_documents() -> list[Document]:
    async def fetch() -> list[Document]:
        async with TestSessionLocal() as session:
            return list((await session.scalars(select(Document))).all())

    return asyncio.run(fetch())


def user_id_for(email: str) -> int:
    async def fetch() -> int:
        async with TestSessionLocal() as session:
            return await session.scalar(select(User.id).where(User.email == email))

    return asyncio.run(fetch())


def first_job_id() -> int:
    async def fetch() -> int:
        async with TestSessionLocal() as session:
            return await session.scalar(select(Job.id).order_by(Job.id).limit(1))

    return asyncio.run(fetch())


def test_every_job_becomes_a_public_document(client: TestClient) -> None:
    counts = run_build()

    assert counts == {"job": len(JOBS), "resume": 0, "application_note": 0}
    assert all(doc.user_id is None for doc in all_documents())


def test_a_resume_and_a_note_belong_to_their_owner(
    client: TestClient, register_user
) -> None:
    protima = register_user("protima@example.com")
    register_user("rahul@example.com", name="Rahul")
    job_id = first_job_id()
    client.put("/me/resume", json={"resume": "13 years of React."}, headers=protima)
    client.post(
        "/applications",
        json={"job_id": job_id, "notes": "Recruiter call on Monday."},
        headers=protima,
    )

    counts = run_build()

    assert counts == {"job": len(JOBS), "resume": 1, "application_note": 1}
    private = [doc for doc in all_documents() if doc.doc_type != "job"]
    owner = user_id_for("protima@example.com")
    assert {doc.user_id for doc in private} == {owner}
    note = next(doc for doc in private if doc.doc_type == "application_note")
    assert note.job_id == job_id
    assert note.content == "Recruiter call on Monday."


def test_an_application_without_notes_is_skipped(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/applications", json={"job_id": first_job_id()}, headers=auth_headers)

    assert run_build()["application_note"] == 0


def test_a_second_run_gives_the_same_table(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.put("/me/resume", json={"resume": "A resume."}, headers=auth_headers)
    run_build()
    first = len(all_documents())

    run_build()

    assert len(all_documents()) == first
