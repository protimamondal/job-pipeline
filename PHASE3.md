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

**Status:** Complete

**Boundary record:**

| Stays in Next.js for now | Moves to FastAPI |
|---|---|
| Existing UI pages and React components. | New `backend/` service. |
| Current job list/detail rendering. | `/health` endpoint. |
| Current draft and copilot UI behavior. | Environment settings. |
| Existing Next.js API routes until their later sub-phases move them. | CORS, request IDs, and structured logging. |
|  | Later sub-phases: jobs/Postgres, auth, draft streaming, and copilot/tool orchestration. |

**Implementation checklist:**

- [x] Record what remains in Next.js and what moves to FastAPI.
- [x] Create the `backend/` Python project and application package.
- [x] Add typed environment settings.
- [x] Add the FastAPI application lifecycle and `/health` endpoint.
- [x] Add configured CORS, request IDs, and structured logging.
- [x] Add and pass the first automated test.
- [x] Configure the web app to call the backend `/health` endpoint.
- [x] Run the complete acceptance check and mark this sub-phase complete.

**Acceptance:** A deployment-style FastAPI process starts, its test passes, and
the web app can call `/health`.

**Carried-forward work:** Request logging is not yet structured. The middleware
in `backend/app/main.py` passes `request_id`, `method`, `path`, and
`status_code` via `logging`'s `extra=`, but the configured format string
(`%(levelname)s %(name)s %(message)s`) references none of those keys, so the
fields are silently dropped and lines log as `INFO job_pipeline
request_completed`. The request ID still reaches the response header. Resolve
before or alongside sub-phase 3, where correlating logs with Langfuse traces
depends on it.

### 1 — Postgres job slice

**Status:** Complete

**Build:** Add Pydantic contracts, a FastAPI dependency for the async database
session, Postgres models, Alembic migrations, seed data, `GET /jobs`, and
`GET /jobs/{id}`. Replace the frontend's TypeScript job stubs with these APIs.

**Implementation checklist:**

- [x] Run Postgres locally and add SQLAlchemy, asyncpg, and Alembic.
- [x] Add the typed `database_url` setting and the `.env` template.
- [x] Add the API contracts in `app/api_schemas.py`.
- [x] Add the `jobs` table in `app/db_models.py`.
- [x] Add the engine, session factory, and request-scoped session dependency in
      `app/db.py`.
- [x] Configure Alembic, generate the first migration, and apply it.
- [x] Seed the seven jobs from the retired frontend stub.
- [x] Add `GET /jobs` and `GET /jobs/{id}`, including the 404 path.
- [x] Add endpoint tests against a separate test database.
- [x] Point the job list, job detail, and draft route at the backend and delete
      the stub rows.
- [x] Run the complete acceptance check and mark this sub-phase complete.

**Acceptance:** The existing job list and detail screens read from
FastAPI/Postgres.

**Local setup notes:** Postgres runs in Docker on host port **5433**, because a
pre-existing Windows PostgreSQL 16 service occupies 5432. Data lives in the
`job_pipeline_pgdata` volume, so the container is disposable.

```powershell
docker run --name job-pipeline-pg -e POSTGRES_USER=job_pipeline -e POSTGRES_PASSWORD=devpassword -e POSTGRES_DB=job_pipeline -p 5433:5432 -v job_pipeline_pgdata:/var/lib/postgresql/data -d postgres:17
uv run alembic upgrade head
uv run python seed.py
```

Tests use a separate `job_pipeline_test` database and swap the session via
`app.dependency_overrides`, so they never touch development data.

**Carried-forward work:** The test fixtures build tables with
`Base.metadata.create_all` rather than running the migrations, so a broken
migration would not fail the suite. Resolve in sub-phase 6, where integration
tests and deploy-time migrations are in scope.

### 2 — Authentication and user pipeline

**Status:** Complete

**Build:** Add password hashing, JWT authentication, a current-user dependency,
applications, status updates, and ownership checks.

**Data model change:** `status` moved off `jobs` and onto a new `applications`
table keyed on `(user_id, job_id)`. A job posting is shared reference data; the
stage someone has reached on it is per-user, so one column on `jobs` could not
hold a true answer for two people at once.

**Implementation checklist:**

- [x] Add the `users` and `applications` models and drop `Job.status`.
- [x] Generate and apply the migration, and fix its autogenerated downgrade.
- [x] Add password hashing in `app/security.py` (pwdlib with Argon2).
- [x] Add the JWT settings and the token helpers alongside it.
- [x] Add the auth contracts: `UserCreate`, `UserLogin`, `UserRead`, `Token`.
- [x] Add `POST /auth/register` and `POST /auth/login`.
- [x] Add the `get_current_user` dependency and `GET /auth/me`.
- [x] Add the application contracts and `GET`/`POST /applications`.
- [x] Add `PATCH` and `DELETE /applications/{id}` with ownership checks.
- [x] Protect `GET /jobs` and `GET /jobs/{id}`.
- [x] Nest the job inside `ApplicationRead` so one request renders a row.
- [x] Add auth, application, and cross-user isolation tests.
- [x] Add the sign-in and create-account forms and the session cookie.
- [x] Split the pipeline (`/`) from the job board (`/jobs`), and add
      add-to-pipeline, status changes, removal, and sign-out.
- [x] Run the complete acceptance check and mark this sub-phase complete.

**Acceptance:** Two users have separate pipelines, and neither can read or
modify the other's records.

**Session handling:** The browser never holds the token in readable form. A
Next route handler under `web/app/api/auth/` calls FastAPI and sets an
httpOnly cookie, so page JavaScript cannot read it; server components read it
with `cookies()` and forward it as a bearer header, and client components post
to route handlers under `web/app/api/applications/` that do the same. The
cookie's `maxAge` matches `access_token_expire_minutes`.

**Ownership:** Every application query filters on `current_user.id`, so another
user's rows are never fetched rather than fetched and then hidden. A row
belonging to someone else returns 404 rather than 403, which would confirm the
id exists.

**Carried-forward work:** Signing out clears the cookie but cannot revoke the
token, which stays valid until it expires. Acceptable while the lifetime is an
hour; revisit if refresh tokens or longer sessions arrive. Sub-phase 5 adds
Redis, which is where a deny-list would live.

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
