import os

from mcp.server import MCPServer

mcp = MCPServer("jobs server")

@mcp.tool()
def search_job(title : str,location:str) -> list[dict]:
    "search for job openings by title and location"

    return [
        {
            "company": "Acme Corp",
            "title": title,
            "location": location,
            "salary": 120000,
        },
        {
            "company": "Globex",
            "title": title,
            "location": location,
            "salary": 500,
        },
    ]

if __name__ == "__main__":
    mcp.run(
       transport= "streamable-http",
       host="0.0.0.0",
       port=int(os.environ.get("PORT", "8001")),
       stateless_http= True,
       json_response=True,
    )
