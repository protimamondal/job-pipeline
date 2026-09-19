from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas import UserCreate, UserRead
from app.db import get_session
from app.db_models import User
from app.security import hash_password

router = APIRouter(prefix="/auth",tags=["auth"])

@router.post("/register",response_model=UserRead, status_code = 201)
async def register_user(payload: UserCreate,session: AsyncSession = Depends(get_session)) -> User:
    result = await session.execute(select(User).where(User.email==payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password = hash_password(payload.password)
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user