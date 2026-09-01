# Phase 3 — FastAPI Backend

Phase 3 turns the Phase 2 demo into a persistent application backend while
preserving the existing UI. Product code is developed here; theory and progress
tracking are handled separately in the study repository.

## How sessions work

- "Start sub-phase N theory" means discuss the material in the study repo; it
  does not authorize product edits here.
- "Start sub-phase N" or "implement sub-phase N" in this repo means follow the
  matching checklist below.
- Protima implements one manageable task at a time. The coding agent explains,
  reviews, tests, and debugs unless explicitly asked to write the whole slice.
- Do not assume backend fluency here. Explain backend fundamentals whenever
  Protima asks, using senior-engineer language and frontend analogies where
  useful.
- Explain Python and FastAPI mechanics at implementation depth when introduced;
  both Protima and Rahul are new to this stack.

## Target architecture

```text
Browser / Next.js (`web/`)
          |
          v
FastAPI application (`backend/`)
  |          |             |
Postgres    Redis      LLM + MCP/external tools
                         |
                      Langfuse
```

Postgres is the source of truth. Redis is used only where caching, rate
limiting, or queued work has a demonstrated purpose. The existing
`mcp-server/` remains a separate tool server.

## Sub-phases

The status and checkboxes in this file are the implementation source of truth.
Update them in the same commit as the related code so a new Codex session can
recover the current product status from the repository and Git history.

### 0 — Boundary and skeleton

**Status:** Not started

**Implementation checklist:**

- [ ] Record what remains in Next.js and what moves to FastAPI.
- [ ] Create the `backend/` Python project and application package.
- [ ] Add typed environment settings.
- [ ] Add the FastAPI application lifecycle and `/health` endpoint.
- [ ] Add configured CORS, request IDs, and structured logging.
- [ ] Add and pass the first automated test.
- [ ] Configure the web app to call the backend `/health` endpoint.
- [ ] Run the complete acceptance check and mark this sub-phase complete.

**Acceptance:** A deployment-style FastAPI process starts, its test passes, and
the web app can call `/health`.

### 1 — Postgres job slice

**Status:** Not started

**Build:** Add Pydantic contracts, a FastAPI dependency for the async database
session, Postgres models, Alembic migrations, seed data, `GET /jobs`, and
`GET /jobs/{id}`. Replace the frontend's TypeScript job stubs with these APIs.

**Acceptance:** The existing job list and detail screens read from
FastAPI/Postgres.

### 2 — Authentication and user pipeline

**Status:** Not started

**Build:** Add password hashing, JWT authentication, a current-user dependency,
applications, status updates, and ownership checks.

**Acceptance:** Two users have separate pipelines, and neither can read or
modify the other's records.

### 3 — Draft streaming and Langfuse

**Status:** Not started

**Build:** Move cover-letter generation to FastAPI, define the SSE event
contract, handle cancellation and partial failures, record the prompt, and add
the first Langfuse trace.

**Acceptance:** The existing draft UI streams through FastAPI, and one complete
run is visible in Langfuse.

### 4 — Copilot and tools

**Status:** Not started

**Build:** Move chat/tool orchestration to FastAPI, connect the MCP server, add
one real external-service integration, and trace tool calls.

**Acceptance:** The existing copilot UI works through FastAPI and renders a real
tool result.

### 5 — Redis and operational controls

**Status:** Not started

**Build:** Add one justified cache, a basic per-user rate limit, and one queued
background job with observable status and retries.

**Acceptance:** Cache hit/miss behavior is provable, excess calls return `429`,
and the worker completes or retries a task as designed.

### 6 — Production release

**Status:** Not started

**Build:** Add integration tests, safe deploy-time migrations, hosted FastAPI,
Postgres, and Redis, update the Vercel environment, and verify live logs and
traces.

**Acceptance:** The public frontend uses the live FastAPI backend; auth,
persistence, both AI surfaces, tools, and traces are verified end to end.

## Guardrails

- Extend this product; do not create a disconnected demo.
- Start with one primary FastAPI service, not premature microservices.
- Add Langfuse with the first real LLM endpoint, not as final cleanup.
- A sub-phase is complete only after its acceptance check passes.
