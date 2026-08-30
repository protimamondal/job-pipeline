# Jobs MCP server

The Phase 2 job-search tool exposed over MCP 2.0 Streamable HTTP. It serves
fake job data for the job-pipeline frontend in `../web`.

## Run locally

```bash
uv sync --frozen
uv run python server.py
```

The endpoint is `http://127.0.0.1:8001/mcp` by default. In a hosted
environment the server binds to `0.0.0.0` and reads the platform-provided
`PORT` variable.

## Deploy to Render

The `Dockerfile` here and the `render.yaml` at the repository root define a
Docker web service. In Render's Blueprint creation flow, point it at this
repository; the blueprint sets `rootDir: mcp-server`. After the service is
live, its MCP endpoint is:

```text
https://<render-service>.onrender.com/mcp
```

This endpoint intentionally has no authentication because it returns only
fixed fake data. Do not use this deployment shape for tools that access real
user or company data.
