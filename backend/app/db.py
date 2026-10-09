from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from collections.abc import AsyncGenerator

from app.settings import get_settings

settings = get_settings()

# echo only outside production: it logs every statement with its bound
# parameters, which in production means user emails and hashed passwords in
# the log stream, plus a lot of noise around each request.
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "local",
    # Render's free Postgres allows few connections and recycles idle ones;
    # pre_ping replaces a connection the server has already closed instead of
    # failing the request with it.
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession,None]:
    async with SessionLocal() as session:
        yield session