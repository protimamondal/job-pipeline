import json
import os
import httpx
import redis.asyncio as redis

from mcp.server import MCPServer

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
        print(f"redis read failed, continuing without cache: {exc}")
    if cached is not None:
        print(f"cache hit {cache_key}")
        return json.loads(cached)

    print(f"cache miss {cache_key}")

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
        print(f"arbeitnow request failed: {exc!r}")
        raise RuntimeError(
            "Job search is temporarily unavailable. Please try again in a moment."
        ) from exc
    except (KeyError, ValueError) as exc:
        print(f"arbeitnow returned unexpected data: {exc!r}")
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
        print(f"redis write failed, result not cached: {exc}") 
    return results

if __name__ == "__main__":
    mcp.run(
       transport= "streamable-http",
       host="0.0.0.0",
       port=int(os.environ.get("PORT", "8001")),
       stateless_http= True,
       json_response=True,
    )
