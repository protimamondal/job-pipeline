from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db_models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user( credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        session: AsyncSession = Depends(get_session))-> User:

    if credentials is None:
        raise  HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await session.get(User,int(subject))
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user