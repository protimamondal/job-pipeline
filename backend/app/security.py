from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash

from app.settings import get_settings

password_hash = PasswordHash.recommended()

def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(password:str, hashed_password:str)-> bool:
    return password_hash.verify(password,hashed_password)

def create_access_token(subject: str)->str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp":expire}
    return jwt.encode(payload, settings.jwt_secret,
                      algorithm=settings.jwt_algorithm)

def decode_access_token(token: str)-> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.InvalidTokenError:
        return None
    return payload.get("sub")