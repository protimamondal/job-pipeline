"""The deploy-time seeding, which decides whether the live jobs page has anything on it.

It runs on every container start, so the property that matters is that a
second run changes nothing: a duplicate set of jobs on every wake-up would be
worse than an empty page.
"""

import asyncio

from sqlalchemy import delete, func, select

from app.db_models import Job
from seed_data import JOBS
from seed_if_empty import seed_if_empty
from tests.conftest import TestSessionLocal, _reset_database


def jobs_in_database() -> int:
    async def count() -> int:
        async with TestSessionLocal() as session:
            return await session.scalar(select(func.count()).select_from(Job))

    return asyncio.run(count())


def run_seed() -> int:
    async def once() -> int:
        async with TestSessionLocal() as session:
            return await seed_if_empty(session)

    return asyncio.run(once())


def empty_the_jobs_table() -> None:
    async def wipe() -> None:
        async with TestSessionLocal() as session:
            await session.execute(delete(Job))
            await session.commit()

    asyncio.run(wipe())


def test_an_empty_table_gets_the_samples() -> None:
    asyncio.run(_reset_database())
    empty_the_jobs_table()

    assert run_seed() == len(JOBS)
    assert jobs_in_database() == len(JOBS)


def test_a_second_run_inserts_nothing() -> None:
    """This runs on every boot, so a no-op second run is the whole point."""
    asyncio.run(_reset_database())
    empty_the_jobs_table()
    run_seed()

    assert run_seed() == 0
    assert jobs_in_database() == len(JOBS)


def test_a_populated_table_is_left_alone() -> None:
    """`_reset_database` already seeds, so this is the normal redeploy case."""
    asyncio.run(_reset_database())

    assert run_seed() == 0
    assert jobs_in_database() == len(JOBS)
