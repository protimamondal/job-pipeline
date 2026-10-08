import json
import logging
import os
import httpx
import redis.asyncio as redis

from mcp.server import MCPServer

from logging_config import configure_logging

configure_logging()
logger = logging.getLogger("job_pipeline")

mcp = MCPServer("jobs server")

redis_client = redis.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6380"),
    decode_responses=True,
    socket_connect_timeout=0.5,
)

CACHE_TTL_SECONDS = 600

@mcp.tool()
async def search_job(title : str,location:str) -> list[dict]:
    "search for job openings by title and location"

    cache_key = f"jobs:{title.lower()}:{location.lower()}"
    cached = None
    try:
        cached = await redis_client.get(cache_key)
    except Exception as exc:
        logger.warning(
            "cache_read_failed",
            extra={"cache_key": cache_key, "error": repr(exc)},
        )
    if cached is not None:
        logger.info("cache_lookup", extra={"cache": "hit", "cache_key": cache_key})
        return json.loads(cached)

    logger.info("cache_lookup", extra={"cache": "miss", "cache_key": cache_key})

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"search": title},
                timeout=10,
            )
            response.raise_for_status()
        jobs = response.json()["data"]
    except httpx.HTTPError as exc:
        logger.error(
            "arbeitnow_request_failed",
            extra={"title": title, "location": location, "error": repr(exc)},
        )
        raise RuntimeError(
            "Job search is temporarily unavailable. Please try again in a moment."
        ) from exc
    except (KeyError, ValueError) as exc:
        logger.error(
            "arbeitnow_unexpected_response",
            extra={"title": title, "location": location, "error": repr(exc)},
        )
        raise RuntimeError(
            "Job search returned an unexpected response. Please try again in a moment."
        ) from exc
    matches = [j for j in jobs if location.lower() in j["location"].lower()]

    results = [
        {
            "company": j["company_name"],
            "title": j["title"],
            "location": j["location"],
            "salary": None,
        }
        for j in matches[:5]
    ]

    try:
        await redis_client.set(cache_key, json.dumps(results), ex=CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning(
            "cache_write_failed",
            extra={"cache_key": cache_key, "error": repr(exc)},
        )
    return results

if __name__ == "__main__":
    mcp.run(
       transport= "streamable-http",
       host="0.0.0.0",
       port=int(os.environ.get("PORT", "8001")),
       stateless_http= True,
       json_response=True,
    )
