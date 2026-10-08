import logging
import time

from fastapi import Depends, HTTPException
from redis.exceptions import RedisError

from app.cache import redis_client
from app.db_models import User
from app.dependencies import get_current_user

logger = logging.getLogger("job_pipeline")

RATE_LIMIT_PER_MINUTE = 20
WINDOW_SECONDS = 60


async def enforce_rate_limit(user: User = Depends(get_current_user)) -> User:
    """Allow at most RATE_LIMIT_PER_MINUTE calls per user per minute.

    Redis is not a hard dependency: if it cannot be reached the request is
    allowed through and the failure is logged at ERROR, since the paid
    endpoints behind this are already behind authentication.
    """
    window = int(time.time() // WINDOW_SECONDS)
    key = f"ratelimit:{user.id}:{window}"

    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, WINDOW_SECONDS)
    except RedisError as exc:
        logger.error(
            "rate_limit_unavailable",
            extra={"user_id": user.id, "error": repr(exc)},
        )
        return user

    if count > RATE_LIMIT_PER_MINUTE:
        logger.warning(
            "rate_limit_exceeded",
            extra={
                "user_id": user.id,
                "count": count,
                "limit": RATE_LIMIT_PER_MINUTE,
            },
        )
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )

    return user