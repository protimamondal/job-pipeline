# AI Job Pipeline

[![CI](https://github.com/protimamondal/job-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/protimamondal/job-pipeline/actions/workflows/ci.yml)

A job-application product with two AI features built into it: a **copilot** that
searches jobs through a Model Context Protocol tool and renders the tool's
progress as UI, and a **cover-letter assistant** that streams markdown and links
each claim back to a visible source.

Both AI surfaces are built with the Vercel AI SDK. The MCP server is written by
hand in Python — not a wrapper around a library example.

| | |
|---|---|
| **Live app** | <https://job-pipeline-weld.vercel.app> |
| **MCP endpoint** | <https://job-pipeline-mcp.onrender.com/mcp> |
| **Stack** | Next.js 16, React 19, TypeScript, Vercel AI SDK 7, Tailwind 4, Python 3.13, MCP 2.0 |

> The job listings and the MCP search results are fixed sample data. The AI
> calls, the streaming, the tool protocol and the failure handling are all real.

## What is actually interesting here

Most AI demos stream text into a box. The work in this repo is the part that
comes after that — what the interface does when the model is slow, wrong, or
cut off halfway.

**Streaming markdown that is never broken.** Markdown arrives one token at a
time, so at any moment the buffer may hold a half-open `**` or an unclosed list.
Rendering that naively makes the page flicker. Streamdown repairs incomplete
markdown, and a small helper hides the one marker case it cannot repair.

**Three different failures, three different screens.** A failure before any
response, a failure in the middle of a stream, and a failure inside an MCP tool
call are not the same event and should not look the same. When a stream dies
halfway, the text that already arrived stays on screen — throwing away partial
work the user was already reading is the wrong default.

**Tool calls as UI, not prose.** An MCP tool call moves through preparing,
searching, result, cancelled and error states. Each renders as its own UI state,
so the user can see what the assistant is doing rather than reading about it
afterwards.

**Citations that point at something.** The model emits source markers, which
become clickable chips that highlight the originating job description or
profile section next to the letter — so a claim can be checked without trusting
it.

**Controls that cannot race.** Copy, regenerate and edit are disabled while a
response streams, so two writers can never fight over the same draft.

## Architecture

```text
Browser
  |
  +-- job list / detail pages (Next.js, sample data)
  |
  +-- /api/draft --- Vercel AI SDK ---> OpenAI
  |
  +-- /api/chat  --- Vercel AI SDK ---> MCP client
                                         |
                                         +--> Python MCP 2.0 server (Render)
```

Both API routes run on the Next.js **server**. The provider key and the MCP URL
are server-side environment variables and never reach browser JavaScript.

```text
web/          Next.js frontend and both API routes
mcp-server/   Python MCP 2.0 server exposing the job-search tool
```

## Phase 3

Phase 3 is now open. It will move persistence, authentication, and AI
orchestration into a FastAPI service while keeping this frontend as the product
UI. Work is divided into small vertical sub-phases with an acceptance check for
each one; implementation has not started yet.

See [PHASE3.md](PHASE3.md) for the ordered implementation map and session
workflow.

## Run it locally

Requires Node.js 22+, Python 3.13+, [uv](https://docs.astral.sh/uv/), Docker,
and an OpenAI API key.

Postgres and Redis both run as containers. The ports are deliberately not the
defaults: another project on the development machine already holds 5432 and
6379.

```bash
docker run -d --name job-pipeline-pg -p 5433:5432   -e POSTGRES_USER=job_pipeline -e POSTGRES_PASSWORD=devpassword   -e POSTGRES_DB=job_pipeline postgres:17
docker run -d --name job-pipeline-redis -p 6380:6379 redis:7-alpine
```

Terminal 1 — the MCP server:

```bash
cd mcp-server
uv sync --frozen
uv run python server.py     # http://127.0.0.1:8001/mcp
```

Terminal 2 — the FastAPI backend:

```bash
cd backend
cp .env.example .env        # then fill in the two CHANGE_ME values
uv sync --frozen
uv run alembic upgrade head
uv run python seed.py
uv run uvicorn app.main:app --reload --port 8000
```

Terminal 3 — the frontend:

```bash
cd web
nvm use
npm ci
npm run dev                 # http://localhost:3000
```

The frontend needs no environment file locally: `NEXT_PUBLIC_BACKEND_URL`
defaults to `http://127.0.0.1:8000`. It holds no API keys at all any more —
every AI call is proxied to FastAPI, which is where the OpenAI key lives.

Redis is optional: without it, searches go to the job board every time and
nothing is rate limited, which is logged but not fatal.

### Tests

```bash
cd backend && uv run pytest        # 73 tests, no containers needed
cd mcp-server && uv run pytest     # 20 tests
```

The backend suite needs the Postgres container, because it runs against a
real `job_pipeline_test` database. Redis is faked, so no container is needed
for it.

## Deploy

**Backend, MCP server, Postgres and Redis → Render.** Create a Blueprint from
this repository; `render.yaml` defines all four. Secrets are marked
`sync: false`, so Render prompts for them on the first deploy rather than
keeping them in git:

| Variable | Value |
|---|---|
| `JOB_PIPELINE_JWT_SECRET` | a long random string |
| `JOB_PIPELINE_OPENAI_API_KEY` | your OpenAI key |
| `JOB_PIPELINE_CORS_ORIGINS` | the Vercel URL, e.g. `["https://job-pipeline.vercel.app"]` |
| `JOB_PIPELINE_MCP_SERVER_URL` | `https://job-pipeline-mcp.onrender.com/mcp` |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | from the Langfuse project |

The database URL and the Redis URL are wired by the blueprint itself. Render
hands out a `postgresql://` connection string, which `Settings` rewrites to
the asyncpg driver — there is nothing to keep in sync by hand.

Migrations run from the container's start command (`alembic upgrade head`)
rather than a Render pre-deploy command, which needs a paid instance type.
That is safe for a single instance; more than one would need the pre-deploy
step so two containers cannot migrate at once.

**Frontend → Vercel.** Import this repository and set the project **Root
Directory** to `web`. One Production environment variable:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | `https://job-pipeline-api.onrender.com` |

Then check both surfaces on the live URL: a cover letter that streams, and a
copilot job search that shows the tool running.

On Render's free plan: the services sleep when idle, so the first request
after a pause is slow; Postgres expires after 30 days; and Redis has no
persistence, so a restart empties the search cache and the rate-limit
counters. None of that loses data, because Postgres is the only source of
truth.

## Known limitations

Kept deliberately, and listed rather than hidden:

- The MCP endpoint is unauthenticated. That is only acceptable because it
  returns public job listings from a third-party API and holds no user data.
  Anything touching real user data needs auth in front of it first.
- There is no background worker, so a rate-limited job board is not retried:
  the search just fails for that user. Deliberate — see sub-phase 5 in
  `PHASE3.md`.
- The rate limiter uses a fixed window, which allows up to twice the limit
  across a minute boundary.
- Copy and Edit still carry the converted citation link syntax.
- A citation marker can flash raw while only part of it has streamed.
- An unrecognised citation marker is not dropped yet.
- Citations resolve to a whole job or profile source, not to individual lines.
- Message branching is understood as a data-model consequence — regenerating
  from earlier state creates a tree — but the version-navigation UI is not built.

Citation accuracy is not a meaningful measurement yet: the prompt permits only
two fixed source identifiers. Validating a citation per retrieved chunk is a
retrieval problem, and belongs with the RAG work rather than here.

## Background

Built by **[Protima Mondal](https://github.com/protimamondal)** as the Phase 2
project of a structured AI engineering programme. The learning log, roadmap and
notes behind it are in
[ai-engineering-journey](https://github.com/protimamondal/ai-engineering-journey).
