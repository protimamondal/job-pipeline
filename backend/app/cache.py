import redis.asyncio as redis

from app.settings import get_settings

redis_client = redis.from_url(
    get_settings().redis_url,
    decode_responses=True,
    socket_connect_timeout=0.5,
)