from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas import ApplicationRead, ApplicationCreate
from app.db import get_session
from app.db_models import Application, User, Job
from app.dependencies import get_current_user

router = APIRouter(prefix="/applications",tags=["application"])

@router.get("",response_model=list[ApplicationRead])
async def list_applications(
    cur_user:User = Depends(get_current_user), 
    session:AsyncSession = Depends(get_session))->list[Application]:
    result = await session.execute(select(Application).where(Application.user_id==cur_user.id)
                             .order_by(Application.id))
    return list(result.scalars().all())

@router.post("",response_model=ApplicationRead,status_code=201)
async def create_application(
    payload: ApplicationCreate,
    cur_user :User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session))->Application:

    job = await session.get(Job,payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = await session.execute(
        select(Application).where(
            Application.user_id == cur_user.id,
            Application.job_id == payload.job_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Job already in your pipeline")

    application = Application(
        user_id= cur_user.id,
        job_id= payload.job_id,
        status= payload.status,
        notes = payload.notes
        )

    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application