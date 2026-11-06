from fastapi import APIRouter, Depends
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas import SearchRequest, SearchResult
from app.db import get_session
from app.db_models import Chunk, User
from app.dependencies import get_current_user
from app.embed_chunks import embed
from app.search import search_chunks
from app.settings import get_settings

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=list[SearchResult])
async def search_endpoint(
    body: SearchRequest,
    cur_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Chunk]:
    client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    vectors = await embed(client, [body.question])
    return await search_chunks(session, cur_user.id, vectors[0])
