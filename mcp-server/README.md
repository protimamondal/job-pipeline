# Jobs MCP server

The Phase 2 job-search tool exposed over MCP 2.0 Streamable HTTP. It searches
live listings from the Arbeitnow API for the job-pipeline frontend in `../web`,
and caches results in Redis.

## Run locally

Start Redis first. Searches work without it, but every call then goes to
Arbeitnow.

```bash
docker start job-pipeline-redis
uv sync --frozen
uv run python server.py
```

If the Redis container does not exist yet:

```bash
docker run -d --name job-pipeline-redis -p 6380:6379 redis:7-alpine
```

The endpoint is `http://127.0.0.1:8001/mcp` by default. In a hosted
environment the server binds to `0.0.0.0` and reads the platform-provided
`PORT` variable.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8001` | Port to bind |
| `REDIS_URL` | `redis://localhost:6380` | Search cache, ten-minute TTL. Optional: if unreachable, every search calls Arbeitnow instead |

Port 6380 rather than the usual 6379 because another project's Redis already
holds 6379 locally, the same reason Postgres runs on 5433 here.

## Deploy to Render

The `Dockerfile` here and the `render.yaml` at the repository root define a
Docker web service. In Render's Blueprint creation flow, point it at this
repository; the blueprint sets `rootDir: mcp-server`. After the service is
live, its MCP endpoint is:

```text
https://<render-service>.onrender.com/mcp
```

This endpoint intentionally has no authentication because it returns only
public job listings from a third-party API and holds no user data. Do not use
this deployment shape for tools that access real user or company data.

Render needs a Redis instance and a `REDIS_URL` variable for this service; see
sub-phase 6 in `../PHASE3.md`.
