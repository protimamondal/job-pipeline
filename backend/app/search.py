from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import Chunk

TOP_K = 5


async def search_chunks(
    session: AsyncSession, user_id: int, question_vector: list[float]
) -> list[Chunk]:
    """Return the closest chunks this user is allowed to see, closest first."""
    query = (
        select(Chunk)
        .where(or_(Chunk.user_id.is_(None), Chunk.user_id == user_id))
        .order_by(Chunk.embedding.cosine_distance(question_vector))
        .limit(TOP_K)
    )
    return list((await session.scalars(query)).all())
