from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api_schemas import ApplicationRead, ApplicationCreate, ApplicationUpdate
from app.db import get_session
from app.db_models import Application, User, Job
from app.dependencies import get_current_user

router = APIRouter(prefix="/applications",tags=["application"])

@router.get("",response_model=list[ApplicationRead])
async def list_applications(
    cur_user:User = Depends(get_current_user), 
    session:AsyncSession = Depends(get_session))->list[Application]:
    result = await session.execute(
        select(Application)
        .where(Application.user_id == cur_user.id)
        .options(selectinload(Application.job))
        .order_by(Application.id)
    )
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
    await session.refresh(application, attribute_names=["job"])
    return application

async def get_owned_application(
    application_id: int,
    cur_user: User,
    session: AsyncSession,
) -> Application:
    """Load one application, but only if it belongs to this user.

    Another user's row is reported as missing rather than forbidden, so the
    endpoint never confirms that an id exists.
    """
    result = await session.execute(
        select(Application)
        .where(
            Application.id == application_id,
            Application.user_id == cur_user.id,
        )
        .options(selectinload(Application.job))
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    cur_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Application:
    application = await get_owned_application(application_id, cur_user, session)

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(application, field, value)

    await session.commit()
    await session.refresh(application)
    await session.refresh(application, attribute_names=["job"])
    return application


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: int,
    cur_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    application = await get_owned_application(application_id, cur_user, session)

    await session.delete(application)
    await session.commit()
