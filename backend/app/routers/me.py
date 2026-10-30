from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas import ResumeRead, ResumeUpdate
from app.db import get_session
from app.db_models import User
from app.dependencies import get_current_user

# Everything here belongs to the logged-in user. There is no user id in any
# URL: the user comes only from the token, so nobody can ask for someone
# else's data.
router = APIRouter(prefix="/me", tags=["me"])


@router.get("/resume", response_model=ResumeRead)
async def read_resume(cur_user: User = Depends(get_current_user)) -> ResumeRead:
    return ResumeRead(resume=cur_user.resume)


@router.put("/resume", response_model=ResumeRead)
async def save_resume(
    body: ResumeUpdate,
    cur_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResumeRead:
    # `get_current_user` loaded this user through the same session (FastAPI
    # builds `get_session` once per request), so changing the attribute and
    # committing is enough: SQLAlchemy writes the UPDATE.
    cur_user.resume = body.resume
    await session.commit()
    return ResumeRead(resume=cur_user.resume)
