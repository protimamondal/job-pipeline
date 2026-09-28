import os
import httpx

from mcp.server import MCPServer

mcp = MCPServer("jobs server")

@mcp.tool()
async def search_job(title : str,location:str) -> list[dict]:
    "search for job openings by title and location"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"search": title},
            timeout=10,
        )
        response.raise_for_status()

    jobs = response.json()["data"]
    matches = [j for j in jobs if location.lower() in j["location"].lower()]

    return [
        {
            "company": j["company_name"],
            "title": j["title"],
            "location": j["location"],
            "salary": None,
        }
        for j in matches[:5]
    ]

if __name__ == "__main__":
    mcp.run(
       transport= "streamable-http",
       host="0.0.0.0",
       port=int(os.environ.get("PORT", "8001")),
       stateless_http= True,
       json_response=True,
    )
