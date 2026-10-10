"""Load the sample jobs into a database that has none, and do nothing otherwise.

The jobs list is browse-only: the product deliberately has no screen and no
route that creates a job, so a freshly provisioned database serves an empty
jobs page until someone loads the samples into it. The free plan gives no
shell inside the running container to do that by hand, so it happens here, in
the start command, straight after the migrations.

Unlike `seed.py`, this deletes nothing. It inserts only when the table is
empty, which is what makes it safe to run on every boot and every deploy --
including after Render's free Postgres expires and is replaced. With more than
one instance two containers could both find the table empty and both insert;
that needs the same pre-deploy step the migrations would.
"""

import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine
from app.db_models import Job
from app.logging_config import configure_logging
from seed_data import JOBS

logger = logging.getLogger("job_pipeline")


async def seed_if_empty(session: AsyncSession) -> int:
    """Insert the sample jobs if there are none. Returns the number inserted."""
    # Count rather than fetch: the descriptions are long, and all this needs
    # to know is whether anything is there at all.
    existing = await session.scalar(select(func.count()).select_from(Job))

    if existing:
        logger.info("seed_skipped", extra={"existing_jobs": existing})
        return 0

    session.add_all([Job(**job) for job in JOBS])
    await session.commit()
    logger.info("seed_inserted", extra={"inserted_jobs": len(JOBS)})
    return len(JOBS)


async def main() -> None:
    async with SessionLocal() as session:
        await seed_if_empty(session)

    await engine.dispose()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
