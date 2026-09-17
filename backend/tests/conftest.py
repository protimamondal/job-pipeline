"""Test fixtures: a separate database, reset and seeded before every test."""

import asyncio
from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import get_session
from app.db_models import Base, Job
from app.main import app
from app.settings import get_settings
from seed_data import JOBS

# Same server, same credentials — a different database.
TEST_DATABASE_URL = get_settings().database_url.rsplit("/", 1)[0] + "/job_pipeline_test"

# NullPool: don't reuse connections, because the reset below and the requests
# themselves run on different event loops.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _reset_database() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        session.add_all([Job(**data) for data in JOBS])
        await session.commit()


async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    asyncio.run(_reset_database())
    app.dependency_overrides[get_session] = _get_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
