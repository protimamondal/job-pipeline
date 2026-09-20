from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas import UserCreate, UserRead, UserLogin, Token
from app.db import get_session
from app.db_models import User
from app.security import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user

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

@router.post("/login",response_model=Token)
async def login_user(payload: UserLogin, session: AsyncSession = Depends(get_session))-> Token:
    result = await session.execute(select(User).where(User.email==payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user