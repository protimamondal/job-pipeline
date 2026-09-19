import asyncio

from sqlalchemy import text

from app.db import SessionLocal, engine
from app.db_models import Job
from seed_data import JOBS


async def main() -> None:
    async with SessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE jobs, applications RESTART IDENTITY"))
        session.add_all([Job(**data) for data in JOBS])
        await session.commit()

    await engine.dispose()


asyncio.run(main())
