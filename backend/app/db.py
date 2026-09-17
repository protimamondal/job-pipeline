from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from collections.abc import AsyncGenerator

from app.settings import get_settings

engine = create_async_engine(get_settings().database_url, echo=True)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession,None]:
    async with SessionLocal() as session:
        yield session