"""Rebuild the `documents` table from jobs, resumes and application notes.

`documents` is the one place RAG reads from, but it is a copy: `jobs`,
`users.resume` and `applications.notes` stay the source of truth. So this
deletes every document and writes them again in one transaction. Running it
twice gives the same table, and a half-finished run leaves the old table in
place.

Jobs are public (`user_id` NULL). A resume and a note belong to one user and
carry their `user_id`, which is what every retrieval query filters on.
Empty resumes and notes are skipped: there is nothing to retrieve.
"""

import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import SessionLocal, engine
from app.db_models import Application, Document, Job, User


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


async def build_documents(session: AsyncSession) -> dict[str, int]:
    """Replace every document. Returns how many of each type were written."""
    jobs = (await session.scalars(select(Job))).all()
    users = (await session.scalars(select(User))).all()
    applications = (
        await session.scalars(
            select(Application).options(selectinload(Application.job))
        )
    ).all()

    documents = [
        Document(
            doc_type="job",
            user_id=None,
            job_id=job.id,
            title=f"{job.title} at {job.company}",
            content=job.description,
        )
        for job in jobs
    ]
    documents += [
        Document(
            doc_type="resume",
            user_id=user.id,
            job_id=None,
            title="Resume",
            content=user.resume,
        )
        for user in users
        if _has_text(user.resume)
    ]
    documents += [
        Document(
            doc_type="application_note",
            user_id=application.user_id,
            job_id=application.job_id,
            title=f"Notes on {application.job.title} at {application.job.company}",
            content=application.notes,
        )
        for application in applications
        if _has_text(application.notes)
    ]

    await session.execute(delete(Document))
    session.add_all(documents)
    await session.commit()

    counts = {"job": 0, "resume": 0, "application_note": 0}
    for document in documents:
        counts[document.doc_type] += 1
    return counts


async def main() -> None:
    async with SessionLocal() as session:
        counts = await build_documents(session)
    await engine.dispose()
    print(f"Documents written: {counts}")


if __name__ == "__main__":
    asyncio.run(main())
