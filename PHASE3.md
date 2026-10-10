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

**Status:** Complete

**Build:** Move cover-letter generation to FastAPI, define the SSE event
contract, handle cancellation and partial failures, record the prompt, and add
the first Langfuse trace.

**Implementation checklist:**

- [x] Fix structured request logging (fields were silently dropped from the
      configured format string).
- [x] Add the `openai` dependency and `openai_api_key`/`draft_model` settings.
- [x] Design the streaming contract: initially a custom `delta`/`error`/`done`
      shape, later replaced with the AI SDK's own real Data Stream / UI
      Message Stream Protocol (`text-start`/`text-delta`/`text-end`/`error`,
      the `x-vercel-ai-ui-message-stream` header, the `[DONE]` terminator) —
      see `PHASE3-SUBPHASE3-CONTRACT.md` for the full contract and why it
      changed.
- [x] Add `POST /jobs/{job_id}/draft`: fetch the job, build the prompt, stream
      the response, and close the upstream OpenAI connection deterministically
      (`async with`) on completion, disconnect, or error.
- [x] Turn `web/app/api/draft/route.ts` into a thin auth-and-pipe proxy to the
      FastAPI endpoint.
- [x] Drop `DraftPanel.tsx`'s `streamProtocol: "text"` override so
      `useCompletion`'s default data-protocol parsing handles the stream
      natively, removing the old `parseDraftStream`/`STREAM_ERROR_MARKER`
      hack entirely.
- [x] Add Langfuse tracing via its wrapped OpenAI client (`langfuse.openai`),
      with `extra="ignore"` on `Settings` so its own unprefixed env vars can
      share `.env` without crashing the app.
- [x] Verify end-to-end: real login, a real request through the Next.js proxy
      into FastAPI, a real OpenAI call, all response frames validated against
      the AI SDK's actual schema, and a real trace confirmed via the Langfuse
      API.
- [x] Run the complete acceptance check and mark this sub-phase complete.

**Acceptance:** The existing draft UI streams through FastAPI, and one complete
run is visible in Langfuse.

**Carried-forward work:** No automated test covers `POST /jobs/{job_id}/draft`
yet — verification so far is live/manual only. `backend/.env.example` doesn't
document the required `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` vars (they
intentionally sit outside the `JOB_PIPELINE_` prefix convention, since
Langfuse's own client reads them directly). Resolve both before sub-phase 4
adds more tool-call complexity on top of this same streaming foundation.

### 4 — Copilot and tools

**Status:** Complete

**Build:** Move chat/tool orchestration to FastAPI, connect the MCP server, add
one real external-service integration, and trace tool calls.

**Implementation checklist:**

- [x] Add the `mcp` Python client dependency and an `mcp_server_url` FastAPI
      setting mirroring the old Next.js env var; prove connectivity by
      listing and calling the real tool before writing any chat logic.
- [x] Add `POST /chat`, protected by the existing auth dependency, accepting
      the same message-history shape the frontend already sends
      (`to_openai_messages` strips it down to plain `{role, content}` —
      historical tool-call replay is a known simplification, not fixed).
- [x] Implement the real AI SDK protocol, extending sub-phase 3's text-part
      foundation with tool parts (`tool-input-start`/`delta`/`available`,
      `tool-output-available`/`error`, `start-step`/`finish-step`) so
      `useChat` needed zero frontend changes.
- [x] Reuse the cancellation pattern (`request.is_disconnected()` +
      `async with`) for the chat stream, plus a 5-round cap on the
      tool-calling loop mirroring the old `stepCountIs(5)`.
- [x] Trace tool calls through Langfuse: wrapped the whole turn in
      `start_as_current_observation(as_type="agent")` so multiple OpenAI
      calls in one turn nest under a single trace — confirmed via the
      Langfuse API (one `AGENT` + two `GENERATION` observations sharing one
      `trace_id`).
- [x] Turn `web/app/api/chat/route.ts` into a thin proxy to FastAPI, matching
      the `/api/draft` pattern.
- [x] Add one real external-service integration to the MCP tool
      (`mcp-server/server.py`'s `search_job` now calls Arbeitnow's live,
      no-auth job board API instead of returning fixed sample data; closes
      the known-limitation noted in the root `README.md`).
- [x] Add auth-gating tests for `/chat` and `/jobs/{job_id}/draft`
      (`tests/test_chat.py`, `tests/test_drafts.py`); confirm the copilot UI
      renders every tool-call state end to end with real data.
- [x] Run the complete acceptance check and mark this sub-phase complete.

**Acceptance:** The existing copilot UI works through FastAPI and renders a real
tool result.

**A real bug found along the way, fixed in both `drafts.py` and `chat.py`:**
`await get_client().flush()` — `flush()` is synchronous, not a coroutine;
awaiting it raised `TypeError` and silently killed the stream right before
`[DONE]`. Also found and fixed: `tool-output-available` was sending the raw
MCP text blocks instead of `result.structured_content`, which would have
crashed `CoPilotPanel.tsx`'s existing rendering code at `.structuredContent.result`.

**Carried-forward work:** The two new tests only confirm auth-gating (401
without a token) — they don't exercise the actual streaming/tool-calling
behavior, which would need `AsyncOpenAI` and the MCP `ClientSession` mocked
to test without hitting real, paid, non-deterministic external services.
Worth doing together with the same gap already noted for `drafts.py` in
sub-phase 3, since both need similar mocking work. `search_job`'s real
integration has no error handling yet for the external API being down or
rate-limited — untested, not just unhandled.

### 5 — Redis and operational controls

**Status:** Complete, with the queued background job deliberately dropped (see
**Scope decision** below)

**Build:** Add one justified cache, a basic per-user rate limit, and one queued
background job with observable status and retries.

**Implementation checklist:**

- [x] Run Redis as a container on port 6380 (6379 was already taken by another
      project's Redis locally, the same reason Postgres runs on 5433 here) and
      add the `redis` Python client. `redis` is the counterpart of `asyncpg`,
      not of SQLAlchemy — Redis has one flat keyspace, so there is no ORM,
      no models and no migrations.
- [x] Cache `search_job` in `mcp-server/server.py` with a cache-aside read,
      a `jobs:{title}:{location}` key, and a 600-second TTL. Ten minutes is a
      staleness decision, not a performance one: job listings change slowly,
      and a candidate seeing a ten-minute-old board is harmless.
- [x] Prove hit/miss behaviour: a cold call takes ~0.6s and logs
      `cache_lookup cache=miss`; the next call takes ~0.001s and logs
      `cache_lookup cache=hit`.
- [x] Degrade gracefully when Redis is unreachable — every Redis call is
      wrapped, failures are logged, and the search still returns live results.
      Losing Redis may only make things slower, never wrong.
- [x] Fix the 4s-per-call stall when Redis is down with
      `socket_connect_timeout=0.5`. Measured: 4.1s default, 0.509s with the
      timeout. Disabling client retries made no difference — the delay was the
      OS-level connect timeout, not retries.
- [x] Handle the Arbeitnow API failing, which sub-phase 4 left as a known gap:
      `httpx.HTTPError` (connect, timeout, bad status) and `KeyError`/
      `ValueError` (unexpected shape) each map to a clean user-facing message,
      with `raise ... from exc` preserving the cause for the logs. Verified
      across all four modes, and verified that no failure is ever cached.
- [x] Add a per-user rate limit of 20 requests per minute on the two endpoints
      that call the LLM (`POST /chat`, `POST /jobs/{job_id}/draft`), as a
      fixed window: `INCR` on `ratelimit:{user_id}:{window}` with the window
      number baked into the key, so expiry needs no cleanup pass.
- [x] Implement it as a FastAPI dependency rather than middleware. Middleware
      runs before dependency resolution, so it has no authenticated user to
      key the limit on. `enforce_rate_limit` depends on `get_current_user` and
      returns the same `User`, leaving `cur_user` unchanged at both call sites.
- [x] Fail open when Redis is unreachable: allow the request, log at ERROR.
      Both endpoints are already behind authentication, so an unauthenticated
      flood is not the threat being defended against.
- [x] Verify over real HTTP with a real logged-in user: counter at the limit
      returns `429` with `Retry-After: 60`, a fresh counter reaches the
      endpoint, and both endpoints are wired.
- [x] Replace the `print()` calls in `mcp-server/server.py` with the same
      `JsonFormatter` the backend uses, so the MCP server's cache hits/misses
      (INFO), Redis failures (WARNING) and Arbeitnow failures (ERROR) are
      structured and greppable in a hosted log stream.
- [ ] One queued background job with observable status and retries —
      **dropped deliberately**, see below.

**Acceptance:** Cache hit/miss behavior is provable, excess calls return `429`,
and the worker completes or retries a task as designed. The first two pass; the
third does not apply after the scope decision below.

**Scope decision — no queue (2026-10-09):** Protima and Rahul decided against
building the worker. Nothing in this product is heavy enough to need one: the
two slow operations are LLM streams that the user is actively watching, and
moving those to a worker would replace streaming with short-polling, which is a
straight UX downgrade on the most visible feature in the app. `arq` was the
library chosen if it had gone ahead, over Celery and RQ, because the backend is
fully async and a sync worker would have to wrap every existing call in
`asyncio.run`. Queueing was studied and prototyped on paper only.

**What this costs us, recorded honestly:** when Arbeitnow returns `429`, the
search still fails permanently for that user — there is nothing to retry it
later. This was logged as a known limitation in sub-phase 4 and the queue was
the intended fix. It remains open.

**Decisions worth remembering:**

- Fixed window over sliding window. A fixed window allows up to 2x the limit
  across a minute boundary; a sliding window (a sorted set of request
  timestamps, trim-count-add) does not, but its three commands are not atomic
  and would need a Lua script to be correct. `INCR` is a single command and
  cannot be raced. The burst was judged acceptable for 20/min on an
  authenticated endpoint.
- Task status, had the queue been built, would have lived in a Postgres
  `tasks` table rather than Redis, to keep Redis disposable.

**Carried-forward work:**

- No automated tests for the cache or the rate limiter — both were verified
  with throwaway scripts that were then deleted. This compounds the gap
  already recorded in sub-phases 3 and 4, where the tests only prove
  auth-gating and never exercise streaming or tool-calling.
- A blocked request still increments the fixed-window counter, so a hammering
  client inflates its own count. Harmless here, but it is why `INCR` cannot
  implement a sliding window.
- If `EXPIRE` fails on its own after a successful `INCR`, that key never
  expires — one leaked key per user per minute, in a case that needs Redis to
  accept one command and reject the next.
- **mcp version drift:** `backend` has mcp 2.2.0, `mcp-server` has 2.0.0. The
  newer version strips the exception text out of tool errors, so the friendly
  Arbeitnow messages added here would be replaced by a generic
  `Error executing tool search_job` if the backend's version were ever matched
  in the MCP server. Verified empirically, not yet resolved.
- `render.yaml` has no Redis service and no `REDIS_URL`; the MCP server there
  will run cache-less until sub-phase 6 adds one.

**Latent bug found along the way, fixed in `backend/app/routers/chat.py`:**
`ClientSession.call_tool` does not raise when a tool fails — it returns a
`CallToolResult` with `is_error=True` and `structured_content=None`. The
existing `except Exception` handler therefore never fired, and a failed tool
was reported to the browser as a success with a null payload, which would crash
`CoPilotPanel.tsx` at `.structuredContent.result`. Now the result's error text
is raised so the existing handler sees it.

### 6 — Production release

**Status:** In progress — everything that can be done from the repository is
done; the remaining items need the Render, Vercel and Langfuse dashboards

**Build:** Add integration tests, safe deploy-time migrations, hosted FastAPI,
Postgres, and Redis, update the Vercel environment, and verify live logs and
traces.

**Implementation checklist:**

- [x] Integration tests, closing the gap carried forward from sub-phases 3, 4
      and 5 where the only tests for the AI routes asserted a 401. 93 tests
      across both projects: the AI SDK event protocol, the tool-calling loop,
      two parallel tool calls, the five-round cap, the draft prompt, each
      Arbeitnow failure mode, cache hit/miss and TTL, and the rate limiter's
      policy, window and fail-open behaviour.
- [x] `tests/fakes.py` replaces OpenAI, the MCP server and Langfuse, so the
      suite costs nothing to run and is deterministic. `FakeRedis` rather than
      the container, because `app.cache.redis_client` is created once at
      import and `TestClient` runs each request on a fresh event loop — a
      pooled connection ends up owned by a closed loop. Under uvicorn there is
      one loop per process, so this is a test artefact, not a production bug.
- [x] A regression test for the sub-phase 5 bug where a failed MCP tool was
      reported to the browser as a success with a null payload.
- [x] A `Dockerfile` for the backend, and `render.yaml` extended from one
      service to four: the FastAPI backend, the MCP server, Postgres, and one
      Key Value instance shared by both web services.
- [x] Safe deploy-time migrations: `alembic upgrade head` in the container's
      start command. Not a Render `preDeployCommand`, which needs a paid
      instance type. Idempotent, so restarts are safe — but see the limitation
      below about more than one instance.
- [x] Fix three things that would only have failed in production:
      `postgresql://` not naming the asyncpg driver (the service would not
      have booted), `echo=True` logging every statement with its bound
      parameters (user emails and password hashes in the log stream), and no
      `pool_pre_ping` against a Postgres that recycles idle connections.
- [x] Verify the image for real: built it, ran it against the local containers
      with a deliberately plain `postgresql://` URL the way Render supplies
      one, and confirmed migrations applied, `/health` returned 200 with
      `environment=production`, register/login/`/auth/me`/`/jobs` all worked,
      and no SQL appeared in the logs.
- [x] Correct the documentation rather than add to it. The README's local
      setup had no backend, Postgres or Redis, and still told the reader to
      put an OpenAI key in the frontend — the frontend has held no keys since
      sub-phase 4 moved every AI call behind FastAPI.
- [x] Create the Render Blueprint and supply the prompted secrets. The first
      deploy failed because every `sync: false` variable was absent rather
      than blank: Render only prompts for them while the Blueprint is being
      created, and nothing is stored if that is skipped, so `Settings` raised
      `jwt_secret Field required` inside `alembic/env.py` before uvicorn
      started. Added `JOB_PIPELINE_JWT_SECRET`, `JOB_PIPELINE_OPENAI_API_KEY`
      and `JOB_PIPELINE_MCP_SERVER_URL` from the service's Environment page.
- [x] Verify the live backend. `/health` returns 200 with
      `environment=production`; register 201, duplicate register 409, login
      200 with a bearer token, `/auth/me` 200, `/jobs` 200, and `/auth/me`
      without a token and login with a wrong password both 401 — so the image,
      the migrations, Postgres and JWT signing are all correct in production.
      The MCP service answers an `initialize` handshake over
      `POST /mcp` and lists its one tool, `search_job`. It has no `/health`
      route, by design, so a 404 there is not a fault.
- [x] Set `NEXT_PUBLIC_BACKEND_URL` on Vercel to the live backend. Adding the
      variable was not enough: a `NEXT_PUBLIC_` value is stamped into the
      bundle at build time, so it took a redeploy. Until then Vercel's server
      fell back to `http://127.0.0.1:8000` and every route crashed with a 500
      — recognisable because a wrong password returned 500 rather than the
      401 the route returns when the backend actually answers.
- [x] Set `JOB_PIPELINE_CORS_ORIGINS` to the Vercel origin. It is a
      `list[str]`, and pydantic-settings parses a complex field from the
      environment as JSON, so the obvious bare URL crashes the service on
      boot with a `JSONDecodeError` that never mentions the variable's shape.
      The value has to be `["https://job-pipeline-weld.vercel.app"]`.
      Calling this the likeliest first failure was wrong: the frontend calls
      FastAPI only from its own `/api/*` route handlers, which run on
      Vercel's server, so the browser never makes a cross-origin request and
      CORS is not on the path at all. Verified anyway — the Vercel origin is
      granted, an unknown origin is not.
- [ ] Create a Langfuse production project and set its three variables, then
      confirm a live trace arrives.
- [x] Run the acceptance check against the live URLs. Everything passes
      except the first request after an idle period: auth, persistence, the
      jobs list, applications, both AI surfaces, the tool loop, and the rate
      limiter (20 allowed, the 21st a 429 with `Retry-After: 60`, counted in
      the real Key Value instance — probed against a missing job id, so it
      cost nothing in tokens).
- [x] Run the acceptance check through the deployed frontend, not only
      against the backend: sign up sets the session cookie, the jobs page
      renders all seven jobs, a job page renders, applying returns 201 and
      the job appears on the board, and `POST /api/draft` streams a
      1,665-character cover letter in 4.5s. A signed-out visitor is
      redirected to `/login`.
- [x] Fix the cold-start failure described below.
- [ ] Re-run the copilot against a genuinely idle MCP service to confirm the
      fix in production, then mark this sub-phase complete.

**Fixed: the first chat after an idle period used to fail.** Both free
services sleep. When the backend was awake and the MCP service was not, the
backend's call had to wait out a cold start that measured 31.4s on two
separate occasions, against `streamable_http_client`'s 30s default general
timeout (`MCP_DEFAULT_TIMEOUT`). It gave up about a second early, so a user's
first message errored and the retry worked. The router now passes its own
`httpx2.AsyncClient` with `mcp_timeout_seconds` (90s) for connect, keeping the
SDK's 300s read timeout, which governs something else: how long a response
stream may stay open.

The second half of the fix is what the failure *said*. anyio re-raises through
a task group, so both the browser and the log got "unhandled errors in a
TaskGroup (1 sub-exception)" and nothing about the cause -- which is why
diagnosing it needed a local script to unwrap the group by hand. `unwrap()`
now walks to the innermost cause, the router logs it with `exc_info`, and the
browser is told what actually happened. A group with several sub-exceptions is
left alone, having no single cause to report.

**Blocked, not broken:**

- ~~The OpenAI account has no credits~~ — credits added, and both AI
  surfaces now work against the live URL. Verified: a plain chat streams back
  `pong`; a chat that needs the tool runs the full two-round loop, calls
  `search_job` over the live MCP service and answers from real Arbeitnow
  results; `POST /jobs/1/draft` streams a 263-delta cover letter citing
  `[[job]]` and `[[profile]]`, an extra `instruction` is honoured, and a
  missing job is still a 404.
- ~~The production `jobs` table is empty~~ — fixed by `seed_if_empty.py`,
  which the container runs straight after the migrations. The jobs list is
  browse-only by design, so nothing in the product can populate a new
  database, and the free plan gives no shell to run `seed.py` by hand. Seeding
  at boot means a new database is never served empty, and it self-heals when
  Render's free Postgres expires after 30 days and is replaced. It inserts
  only into an empty table and deletes nothing — unlike `seed.py`, whose
  `TRUNCATE` makes it unsafe to point at production. Verified on the real
  image against a fresh database: the migrations ran, 7 jobs were inserted,
  and a restart logged `seed_skipped` and left the count at 7.

**Acceptance:** The public frontend uses the live FastAPI backend; auth,
persistence, both AI surfaces, tools, and traces are verified end to end.

**Free-plan consequences, accepted:** services sleep when idle, so the first
request after a pause is slow and may look broken; Render's free Postgres
expires after 30 days; the Key Value instance has no persistence, so a restart
empties the search cache and the rate-limit counters. None of that loses data,
because Postgres is the only source of truth — which is the property
sub-phase 5 was built around.

**Carried-forward work:**

- Migrating from the start command only holds for a single instance. Two
  containers starting together would both run `alembic upgrade head` at once;
  that needs a `preDeployCommand`, and so a paid instance type.
- No CI. The tests exist and need no containers except Postgres, so wiring
  them to run on push is the obvious next step and is not done.
- The mcp version drift from sub-phase 5 is still unresolved (`backend` 2.2.0,
  `mcp-server` 2.0.0), and 2.2.0 strips the exception text that carries the
  friendly Arbeitnow messages.

## Guardrails

- Extend this product; do not create a disconnected demo.
- Start with one primary FastAPI service, not premature microservices.
- Add Langfuse with the first real LLM endpoint, not as final cleanup.
- A sub-phase is complete only after its acceptance check passes.
